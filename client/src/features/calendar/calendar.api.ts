/**
 * Calendar API (NUMA-114 P4, PLAN 17.5 / 21.2 / 22.2).
 *
 * Typed fetchers built on the shared `http` client, replacing the per-feature
 * `authHeaders`/`parseJsonResponse` helpers that lived in
 * `components/calendar/api.ts`. Per-endpoint fallback error text is preserved
 * via `errorMessage` (the backend `{ detail }` still wins) and responses are
 * validated with the feature's zod schemas.
 *
 * Behavior notes carried over deliberately:
 * - `fetchCalendarEvents` no longer throws the `CALENDAR_NOT_CONNECTED`
 *   sentinel string; a disconnected calendar surfaces as `ApiError` with
 *   status 401 and the real backend detail (PLAN features/README migration
 *   notes). `lib/stores/calendarStore.ts` inspects the typed error.
 * - `startCalendarWatch` still swallows the two expected local/dev failures.
 * - `sendAgentCommand` still honours the local AI toggle and the
 *   200-with-`{ success: false }` agent envelope.
 * - the SSE stream uses `EventSource` directly (no fetch wrapper applies) on
 *   the same relative `/api` proxy path as before.
 *
 * `expectBody` guards every endpoint that dereferences its response. `http`
 * resolves a body-less or non-JSON 2xx to `undefined` (a proxy that drops the
 * content-type header is enough), which would otherwise surface as an opaque
 * "cannot read properties of undefined" instead of the endpoint's error.
 * `checkCalendarTokenHealth` and `sendAgentCommand` are deliberately exempt:
 * both treat an absent body as a defined fallback value.
 */
import { expectBody, ApiError, http } from "@/lib/http"
import { getLocalAiEnabled } from "@/lib/aiSettings"
import {
  agentChatResponseSchema,
  calendarEventDtoSchema,
  deleteResponseSchema,
  eventsResponseSchema,
  oauthStartResponseSchema,
  tokenHealthSchema,
  watchStartResponseSchema,
} from "./calendar.schema"
import { toCalendarEvent } from "./calendar.transforms"
import type {
  AgentChatMessage,
  AgentChatResponse,
  CalendarEvent,
  CalendarEventPayload,
  TokenHealthResult,
} from "./calendar.types"

const CALENDAR_STREAM_PATH = "/api/calendar/events/stream"

export async function fetchCalendarEvents(opts?: { refresh?: boolean }): Promise<CalendarEvent[]> {
  const message = "Failed to load events"
  const data = await expectBody(
    http.get("/calendar/events", {
      query: opts?.refresh ? { refresh: true } : undefined,
      cache: "no-store",
      schema: eventsResponseSchema,
      errorMessage: message,
    }),
    message
  )

  return data.events.map(toCalendarEvent)
}

export async function createCalendarEvent(payload: CalendarEventPayload): Promise<CalendarEvent> {
  const message = "Failed to create event"
  const created = await expectBody(
    http.post("/calendar/events", payload, {
      schema: calendarEventDtoSchema,
      errorMessage: message,
    }),
    message
  )

  return toCalendarEvent(created)
}

export async function updateCalendarEvent(
  eventId: string,
  payload: CalendarEventPayload
): Promise<CalendarEvent> {
  const message = "Failed to update event"
  const updated = await expectBody(
    http.put(`/calendar/events/${eventId}`, payload, {
      schema: calendarEventDtoSchema,
      errorMessage: message,
    }),
    message
  )

  return toCalendarEvent(updated)
}

export async function deleteCalendarEvent(eventId: string): Promise<boolean> {
  const message = "Failed to delete event"
  const data = await expectBody(
    http.del(`/calendar/events/${eventId}`, {
      schema: deleteResponseSchema,
      errorMessage: message,
    }),
    message
  )

  return data.success
}

/** Local/dev deployments run without a public webhook URL or a Google connection. */
function isExpectedWatchFailure(detail: string): boolean {
  return (
    /GOOGLE_WEBHOOK_BASE_URL\s+is\s+not\s+configured/i.test(detail) ||
    /google\s+calendar\s+is\s+not\s+connected/i.test(detail)
  )
}

export async function startCalendarWatch(): Promise<boolean> {
  try {
    const message = "Failed to start calendar watch"
    const data = await expectBody(
      http.post("/calendar/watch/start", undefined, {
        schema: watchStartResponseSchema,
        errorMessage: message,
      }),
      message
    )
    return data.success
  } catch (error) {
    if (error instanceof ApiError && isExpectedWatchFailure(error.detail)) return false
    throw error
  }
}

export async function getGoogleCalendarAuthorizationUrl(): Promise<string> {
  const message = "Failed to start Google Calendar authorization"
  const data = await expectBody(
    http.post("/calendar/oauth/start", undefined, {
      schema: oauthStartResponseSchema,
      errorMessage: message,
    }),
    message
  )

  if (!data.authorization_url) throw new Error("Google authorization URL was not returned")

  return data.authorization_url
}

const DISCONNECTED: TokenHealthResult = { valid: false, connected: false }

/**
 * Actively validates the stored Google token by pinging the real Google API.
 * Any failed response reads as disconnected, including a body-less or non-JSON
 * one (`http` resolves those to undefined), so callers never see undefined.
 * A schema mismatch still throws, so contract drift stays loud.
 */
export async function checkCalendarTokenHealth(): Promise<TokenHealthResult> {
  try {
    const data = await http.get("/calendar/token/health", {
      cache: "no-store",
      schema: tokenHealthSchema,
    })
    return data ?? DISCONNECTED
  } catch (error) {
    if (error instanceof ApiError) return DISCONNECTED
    throw error
  }
}

export function subscribeToCalendarUpdates(onUpdate: () => void): () => void {
  const source = new EventSource(CALENDAR_STREAM_PATH)
  const handleUpdate = () => onUpdate()

  source.addEventListener("calendar-updated", handleUpdate as EventListener)

  return () => {
    source.removeEventListener("calendar-updated", handleUpdate as EventListener)
    source.close()
  }
}

export async function sendAgentCommand(
  query: string,
  history: AgentChatMessage[] = [],
  signal?: AbortSignal
): Promise<AgentChatResponse> {
  if (!getLocalAiEnabled()) throw new Error("AI agents are disabled in Settings.")

  const data = await http.post("/agent/chat", { query, history }, {
    signal,
    schema: agentChatResponseSchema,
    errorMessage: "Agent request failed",
  })

  if (data.success === false) throw new Error(data.response || "Agent request failed")

  return data ?? { response: "No response received." }
}
