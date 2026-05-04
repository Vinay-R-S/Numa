export type AiProvider = "groq" | "openai" | "anthropic" | "gemini" | "ollama"

export interface AiSettings {
  provider: AiProvider
  model_id: string
  has_api_key: boolean
  ollama_base_url?: string | null
  temperature: number
}

export interface ProviderInfo {
  id: AiProvider
  name: string
  configured_via_env: boolean
  models: string[]
  default_model: string
}

export interface ProvidersListResponse {
  providers: ProviderInfo[]
  current: AiSettings | null
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

function getAuthHeaders(): Record<string, string> {
  if (typeof window === "undefined") return {}
  const token = localStorage.getItem("numa_token")
  if (!token) return {}
  return { Authorization: `Bearer ${token}` }
}

export async function fetchAiSettings(): Promise<ProvidersListResponse> {
  const res = await fetch(`${API_BASE}/api/ai-settings`, {
    headers: { ...getAuthHeaders(), "Content-Type": "application/json" },
  })
  if (!res.ok) throw new Error(`Failed to fetch AI settings: ${res.status}`)
  return res.json()
}

export async function updateAiSettings(body: {
  provider: AiProvider
  model_id: string
  api_key?: string | null
  ollama_base_url?: string | null
  temperature?: number
}): Promise<AiSettings> {
  const res = await fetch(`${API_BASE}/api/ai-settings`, {
    method: "PUT",
    headers: { ...getAuthHeaders(), "Content-Type": "application/json" },
    body: JSON.stringify(body),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || `Failed to update AI settings: ${res.status}`)
  }
  return res.json()
}

export async function resetAiSettings(): Promise<void> {
  const res = await fetch(`${API_BASE}/api/ai-settings`, {
    method: "DELETE",
    headers: getAuthHeaders(),
  })
  if (!res.ok) throw new Error(`Failed to reset AI settings: ${res.status}`)
}

const LOCAL_ENABLED_KEY = "numa_ai_enabled"

export function getLocalAiEnabled(): boolean {
  if (typeof window === "undefined") return true
  const raw = localStorage.getItem(LOCAL_ENABLED_KEY)
  return raw === null ? true : raw === "true"
}

export function setLocalAiEnabled(enabled: boolean): void {
  if (typeof window !== "undefined") {
    localStorage.setItem(LOCAL_ENABLED_KEY, String(enabled))
  }
}
