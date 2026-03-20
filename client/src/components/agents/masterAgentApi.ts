import { getAiSettings } from "@/lib/aiSettings"

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
  history: MasterAgentMessage[] = []
): Promise<MasterAgentResponse> {
  const aiSettings = getAiSettings()
  if (!aiSettings.enabled) {
    throw new Error("AI agents are disabled in Settings.")
  }

  const response = await fetch(`/api/master-agent/chat`, {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify({ query, history, model: aiSettings.modelPreset }),
  })

  const data = await parseJsonResponse<MasterAgentResponse>(response, "Master agent request failed")
  if (data.success === false) {
    throw new Error(data.response || "Master agent request failed")
  }

  return data
}
