import { getLocalAiEnabled } from "@/lib/aiSettings"

export interface MasterAgentMessage {
  role: "user" | "assistant"
  content: string
}

export interface MasterAgentResponse {
  response: string
  success: boolean
  delegated_to?: string | null
  refreshCalendar?: boolean
  refreshTasks?: boolean
  refreshSlack?: boolean
  refreshHealth?: boolean
  refreshGithub?: boolean
  refreshJournal?: boolean
}

export interface MasterAgentFetchLatestResponse {
  ok: boolean
  scope: string
  users: number
  results: Array<{
    user_id: string
    calendar: { ok: boolean; fetched: number; detail: string }
    slack: { ok: boolean; fetched: number; channels?: number; detail: string }
  }>
  retention: Record<string, unknown>
}

interface FetchLatestOptions {
  background?: boolean
}

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

export async function sendMasterAgentCommand(
  query: string,
  history: MasterAgentMessage[] = [],
  signal?: AbortSignal
): Promise<MasterAgentResponse> {
  if (!getLocalAiEnabled()) {
    throw new Error("AI agents are disabled in Settings.")
  }

  const response = await fetch(`/api/master-agent/chat`, {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify({ query, history }),
    signal,
  })

  const data = await parseJsonResponse<MasterAgentResponse>(response, "Master agent request failed")
  if (data.success === false) {
    throw new Error(data.response || "Master agent request failed")
  }

  return data
}

export async function fetchLatestAgentData(
  options: FetchLatestOptions = {}
): Promise<MasterAgentFetchLatestResponse> {
  const qs = new URLSearchParams()
  if (options.background) qs.set("background", "true")

  const response = await fetch(`/api/master-agent/fetch-latest${qs.size ? `?${qs.toString()}` : ""}`, {
    method: "POST",
    headers: authHeaders(),
  })

  return parseJsonResponse<MasterAgentFetchLatestResponse>(
    response,
    "Failed to fetch latest app data"
  )
}
