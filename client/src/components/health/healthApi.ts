/**
 * Health Sub-Agent API client
 * All calls go through /api/* which Next.js proxies to FastAPI.
 */

// ── Types ──────────────────────────────────────────────────────────────────────

export interface HealthAgentMessage {
  role: "user" | "assistant"
  content: string
}

export interface HealthChatResponse {
  response: string
  success: boolean
  delegated_to?: string | null
  refresh_health?: boolean
}

export interface HealthSnapshot {
  id: string
  user_id: string
  source: string
  snapshot_date: string
  steps: number | null
  active_minutes: number | null
  calories: number | null
  distance_km: number | null
  sleep_hours: number | null
  sleep_stages: { deep?: number; light?: number; rem?: number; generic?: number } | null
  activities: Record<string, number> | Array<Record<string, unknown>> | null
  created_at?: string | null
  updated_at?: string | null
}

export interface HealthStatus {
  google_fit_configured: boolean
  strava_configured: boolean
  snapshots_today: number
  total_snapshots: number
}

export interface HealthSyncResult {
  ok: boolean
  source: string
  snapshot_date?: string | null
  detail?: string | null
}

// ── Helpers ────────────────────────────────────────────────────────────────────

function authHeaders(): HeadersInit {
  const token = typeof window !== "undefined" ? localStorage.getItem("numa_token") : null
  return {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  }
}

async function parseJson<T>(res: Response, fallback: string): Promise<T> {
  if (!res.ok) {
    let detail = fallback
    try {
      const body = await res.json()
      if (typeof body?.detail === "string") detail = body.detail
    } catch {
      // keep fallback
    }
    throw new Error(detail)
  }
  return res.json() as Promise<T>
}

// ── Status ─────────────────────────────────────────────────────────────────────

export async function getHealthStatus(): Promise<HealthStatus> {
  const res = await fetch("/api/health-agent/status", { headers: authHeaders() })
  return parseJson<HealthStatus>(res, "Failed to fetch health status")
}

// ── Snapshots ──────────────────────────────────────────────────────────────────

export async function getHealthSnapshots(params?: {
  source?: string
  days?: number
}): Promise<HealthSnapshot[]> {
  const qs = new URLSearchParams()
  if (params?.source) qs.set("source", params.source)
  if (params?.days) qs.set("days", String(params.days))

  const res = await fetch(`/api/health-agent/snapshots?${qs.toString()}`, {
    headers: authHeaders(),
  })
  return parseJson<HealthSnapshot[]>(res, "Failed to fetch health snapshots")
}

// ── Sync ───────────────────────────────────────────────────────────────────────

export async function syncGoogleFit(): Promise<HealthSyncResult> {
  const res = await fetch("/api/health-agent/sync/google-fit", {
    method: "POST",
    headers: authHeaders(),
  })
  return parseJson<HealthSyncResult>(res, "Failed to sync Google Fit")
}

export async function syncStrava(): Promise<HealthSyncResult> {
  const res = await fetch("/api/health-agent/sync/strava", {
    method: "POST",
    headers: authHeaders(),
  })
  return parseJson<HealthSyncResult>(res, "Failed to sync Strava")
}

export async function syncAllHealth(): Promise<Record<string, unknown>> {
  const res = await fetch("/api/health-agent/sync/all", {
    method: "POST",
    headers: authHeaders(),
  })
  return parseJson<Record<string, unknown>>(res, "Failed to sync health data")
}

// ── Chat ───────────────────────────────────────────────────────────────────────

export async function sendHealthAgentCommand(
  query: string,
  history: HealthAgentMessage[] = []
): Promise<HealthChatResponse> {
  const res = await fetch("/api/health-agent/chat", {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify({ query, history }),
  })
  const data = await parseJson<HealthChatResponse>(res, "Health agent request failed")
  if (data.success === false) {
    throw new Error(data.response || "Health agent request failed")
  }
  return data
}
