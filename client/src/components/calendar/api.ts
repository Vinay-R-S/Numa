import { getAiSettings } from "@/lib/aiSettings"

export interface CalendarEvent {
  id: string
  title: string
  date: Date
  startTime: string
  endTime: string
  description: string
  color?: string
  calendarName?: string
  readonly?: boolean
}

export interface CalendarEventPayload {
  title: string
  date: string
  startTime: string
  endTime: string
  description: string
}

interface EventsApiResponse {
  events: Array<{
    id: string
    title: string
    date: string
    startTime: string
    endTime: string
    description: string
    color?: string
    calendarName?: string
    readonly?: boolean
  }>
}

interface AgentApiResponse {
  response: string
  success?: boolean
  refreshCalendar?: boolean
}

export interface AgentChatMessage {
  role: "user" | "assistant"
  content: string
}

interface DeleteResponse {
  success: boolean
}

interface WatchStartResponse {
  success: boolean
}

interface OAuthStartResponse {
  authorization_url: string
}

const CALENDAR_WINDOW_DAYS = 7

function authHeaders() {
  const token = typeof window !== "undefined" ? localStorage.getItem("numa_token") : null
  return {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  }
}

async function parseJsonResponse<T>(response: Response, fallbackMessage: string): Promise<T> {
  if (!response.ok) {
    let detail = fallbackMessage

    try {
      const body = await response.json()
      if (typeof body?.detail === "string") {
        detail = body.detail
      }
    } catch {
      // Keep fallback message when no JSON body is available.
    }

    throw new Error(detail)
  }

  return response.json() as Promise<T>
}

export async function fetchCalendarEvents(days: number = CALENDAR_WINDOW_DAYS): Promise<CalendarEvent[]> {
  const safeDays = Math.max(1, Math.min(days, CALENDAR_WINDOW_DAYS))
  const response = await fetch(`/api/calendar/events?days=${safeDays}`, {
    headers: authHeaders(),
    cache: "no-store",
  })

  const data = await parseJsonResponse<EventsApiResponse>(response, "Failed to load events")

  return (data?.events ?? []).map((event) => ({
    ...event,
    date: new Date(event.date),
  }))
}

export async function createCalendarEvent(payload: CalendarEventPayload): Promise<CalendarEvent> {
  const response = await fetch(`/api/calendar/events`, {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify(payload),
  })

  const data = await parseJsonResponse<EventsApiResponse["events"][number]>(
    response,
    "Failed to create event"
  )
  return { ...data, date: new Date(data.date) }
}

export async function updateCalendarEvent(
  eventId: string,
  payload: CalendarEventPayload
): Promise<CalendarEvent> {
  const response = await fetch(`/api/calendar/events/${eventId}`, {
    method: "PUT",
    headers: authHeaders(),
    body: JSON.stringify(payload),
  })

  const data = await parseJsonResponse<EventsApiResponse["events"][number]>(
    response,
    "Failed to update event"
  )
  return { ...data, date: new Date(data.date) }
}

export async function deleteCalendarEvent(eventId: string): Promise<boolean> {
  const response = await fetch(`/api/calendar/events/${eventId}`, {
    method: "DELETE",
    headers: authHeaders(),
  })
  const data = await parseJsonResponse<DeleteResponse>(response, "Failed to delete event")
  return data.success
}

export async function startCalendarWatch(): Promise<boolean> {
  const response = await fetch(`/api/calendar/watch/start`, {
    method: "POST",
    headers: authHeaders(),
  })

  if (response.ok) {
    const data = (await response.json()) as WatchStartResponse
    return data.success
  }

  let detail = "Failed to start calendar watch"
  try {
    const body = await response.json()
    if (typeof body?.detail === "string") {
      detail = body.detail
    }
  } catch {
    // Keep fallback message when no JSON body is available.
  }

  // Local/dev mode may intentionally run without a public webhook callback URL.
  if (/GOOGLE_WEBHOOK_BASE_URL\s+is\s+not\s+configured/i.test(detail)) {
    return false
  }

  // Web OAuth may not be connected yet for this user.
  if (/google\s+calendar\s+is\s+not\s+connected/i.test(detail)) {
    return false
  }

  throw new Error(detail)
}

export async function getGoogleCalendarAuthorizationUrl(): Promise<string> {
  const response = await fetch(`/api/calendar/oauth/start`, {
    method: "POST",
    headers: authHeaders(),
  })

  const data = await parseJsonResponse<OAuthStartResponse>(
    response,
    "Failed to start Google Calendar authorization"
  )

  if (!data.authorization_url) {
    throw new Error("Google authorization URL was not returned")
  }

  return data.authorization_url
}

export function subscribeToCalendarUpdates(onUpdate: () => void): () => void {
  const source = new EventSource(`/api/calendar/events/stream`)
  const handleUpdate = () => onUpdate()

  source.addEventListener("calendar-updated", handleUpdate as EventListener)

  return () => {
    source.removeEventListener("calendar-updated", handleUpdate as EventListener)
    source.close()
  }
}

export async function sendAgentCommand(
  query: string,
  history: AgentChatMessage[] = []
): Promise<AgentApiResponse> {
  const aiSettings = getAiSettings()
  if (!aiSettings.enabled) {
    throw new Error("AI agents are disabled in Settings.")
  }

  const response = await fetch(`/api/agent/chat`, {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify({ query, history, model: aiSettings.modelPreset }),
  })

  const data = await parseJsonResponse<AgentApiResponse>(response, "Agent request failed")

  if (data.success === false) {
    throw new Error(data.response || "Agent request failed")
  }

  return data ?? { response: "No response received." }
}
