"use client"

interface BootstrapNextAction {
  service: string
  type: "oauth_redirect"
  authorization_url?: string
}

interface BootstrapResponse {
  ok: boolean
  sync_started?: boolean
  next_action?: BootstrapNextAction | null
}

const BOOTSTRAP_FLAG = "numa_integration_bootstrap_pending"
const BOOTSTRAP_VISITED = "numa_integration_bootstrap_visited"

function getVisited(): string[] {
  try {
    return JSON.parse(localStorage.getItem(BOOTSTRAP_VISITED) || "[]")
  } catch {
    return []
  }
}

function setVisited(visited: string[]) {
  localStorage.setItem(BOOTSTRAP_VISITED, JSON.stringify(Array.from(new Set(visited))))
}

export function markIntegrationBootstrapPending() {
  localStorage.setItem(BOOTSTRAP_FLAG, "1")
  localStorage.removeItem(BOOTSTRAP_VISITED)
}

export function hasIntegrationBootstrapPending() {
  return localStorage.getItem(BOOTSTRAP_FLAG) === "1"
}

export function clearIntegrationBootstrapPending() {
  localStorage.removeItem(BOOTSTRAP_FLAG)
  localStorage.removeItem(BOOTSTRAP_VISITED)
}

export async function runIntegrationBootstrap(token: string): Promise<"redirected" | "done"> {
  const res = await fetch("/api/auth/bootstrap", {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
  })

  if (!res.ok) {
    clearIntegrationBootstrapPending()
    return "done"
  }

  const data = (await res.json()) as BootstrapResponse
  const action = data.next_action

  if (action?.type === "oauth_redirect" && action.authorization_url) {
    const visited = getVisited()
    if (!visited.includes(action.service)) {
      setVisited([...visited, action.service])
      localStorage.setItem(BOOTSTRAP_FLAG, "1")
      window.location.href = action.authorization_url
      return "redirected"
    }
  }

  clearIntegrationBootstrapPending()
  return "done"
}
