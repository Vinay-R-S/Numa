/**
 * Health API (NUMA-116 P4, PLAN 17.5 / 21.2 / 22.2).
 *
 * Typed fetchers built on the shared `http` client, replacing the per-feature
 * `authHeaders`/`parseJson` helpers that lived in `components/health/healthApi.ts`.
 * Per-endpoint fallback error text is preserved via `errorMessage` (the backend
 * `{ detail }` still wins) and responses are validated with the feature's zod
 * schemas.
 *
 * Behavior notes carried over deliberately:
 * - `sendHealthAgentCommand` still throws on the 200-with-`{ success: false }`
 *   agent envelope, and still forwards an external abort untouched so the hook
 *   can tell "user pressed Stop" from a real failure.
 * - `syncGoogleFit`/`syncStrava` are exported even though the page only calls
 *   `syncAllHealth`, so the per-provider surface is not lost in the move.
 * - Every endpoint here answers with JSON. `http` resolves a body-less or
 *   non-JSON 2xx to `undefined` (a proxy dropping the content-type header is
 *   enough), which would put `undefined` into React state and crash the next
 *   render, so `expectBody` turns that into the endpoint's error.
 */
import { expectBody, http } from "@/lib/http"
import {
  healthChatResponseSchema,
  healthIntradaySchema,
  healthSnapshotListSchema,
  healthStatusSchema,
  healthSyncAllResultSchema,
  healthSyncResultSchema,
} from "./health.schema"
import type {
  HealthAgentMessage,
  HealthChatResponse,
  HealthIntraday,
  HealthSnapshot,
  HealthStatus,
  HealthSyncAllResult,
  HealthSyncResult,
} from "./health.types"

export function getHealthStatus(): Promise<HealthStatus> {
  const message = "Failed to fetch health status"
  return expectBody(
    http.get("/health-agent/status", { schema: healthStatusSchema, errorMessage: message }),
    message
  )
}

export function getHealthSnapshots(params?: {
  source?: string
  days?: number
}): Promise<HealthSnapshot[]> {
  const message = "Failed to fetch health snapshots"
  return expectBody(
    http.get("/health-agent/snapshots", {
      query: { source: params?.source || undefined, days: params?.days || undefined },
      schema: healthSnapshotListSchema,
      errorMessage: message,
    }),
    message
  )
}

export function getHealthIntraday(params: {
  snapshotDate: string
  source?: string
}): Promise<HealthIntraday> {
  const message = "Failed to fetch daily health data"
  return expectBody(
    http.get("/health-agent/intraday", {
      query: { snapshot_date: params.snapshotDate, source: params.source || "google_fit" },
      schema: healthIntradaySchema,
      errorMessage: message,
    }),
    message
  )
}

export function syncGoogleFit(): Promise<HealthSyncResult> {
  const message = "Failed to sync Google Fit"
  return expectBody(
    http.post("/health-agent/sync/google-fit", undefined, {
      schema: healthSyncResultSchema,
      errorMessage: message,
    }),
    message
  )
}

export function syncStrava(): Promise<HealthSyncResult> {
  const message = "Failed to sync Strava"
  return expectBody(
    http.post("/health-agent/sync/strava", undefined, {
      schema: healthSyncResultSchema,
      errorMessage: message,
    }),
    message
  )
}

export function syncAllHealth(): Promise<HealthSyncAllResult> {
  const message = "Failed to sync health data"
  return expectBody(
    http.post("/health-agent/sync/all", undefined, {
      schema: healthSyncAllResultSchema,
      errorMessage: message,
    }),
    message
  )
}

export async function sendHealthAgentCommand(
  query: string,
  history: HealthAgentMessage[] = [],
  signal?: AbortSignal
): Promise<HealthChatResponse> {
  const message = "Health agent request failed"
  const data = await expectBody(
    http.post("/health-agent/chat", { query, history }, {
      signal,
      schema: healthChatResponseSchema,
      errorMessage: message,
    }),
    message
  )

  if (data.success === false) throw new Error(data.response || message)

  return data
}
