"use client"

import { OAUTH_AUTHORIZE_URL_PREFIXES, isAllowedExternalUrl } from "./externalUrl"

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

// Every storage access here is wrapped. localStorage throws outright in a
// browser configured to block site data and in some privacy modes, and the
// parsed value was cast to `string[]` with no array check, so a stored object
// or number reached `.includes` and threw (NUMA-142 P6, PLAN 22.2).
function readStorage(key: string): string | null {
  try {
    return localStorage.getItem(key)
  } catch {
    return null
  }
}

function writeStorage(key: string, value: string): void {
  try {
    localStorage.setItem(key, value)
  } catch {
    // A viewer who blocks site data simply repeats the bootstrap next time.
  }
}

function removeStorage(key: string): void {
  try {
    localStorage.removeItem(key)
  } catch {
    // Nothing to do: the value was never readable either.
  }
}

function getVisited(): string[] {
  try {
    const parsed = JSON.parse(readStorage(BOOTSTRAP_VISITED) || "[]")
    if (!Array.isArray(parsed)) return []
    return parsed.filter((entry): entry is string => typeof entry === "string")
  } catch {
    return []
  }
}

function setVisited(visited: string[]) {
  writeStorage(BOOTSTRAP_VISITED, JSON.stringify(Array.from(new Set(visited))))
}

export function markIntegrationBootstrapPending() {
  writeStorage(BOOTSTRAP_FLAG, "1")
  removeStorage(BOOTSTRAP_VISITED)
}

export function hasIntegrationBootstrapPending() {
  return readStorage(BOOTSTRAP_FLAG) === "1"
}

export function clearIntegrationBootstrapPending() {
  removeStorage(BOOTSTRAP_FLAG)
  removeStorage(BOOTSTRAP_VISITED)
}

/**
 * Three outcomes, not two:
 *   "redirected" - the browser is leaving for an OAuth consent screen.
 *   "done"       - bootstrap finished; the pending flag is cleared.
 *   "retry"      - it did not finish and should be tried again on the next
 *                  load. The pending flag stays set, and callers must not treat
 *                  this as success: `"done"` means "go to /home", and returning
 *                  it for a transient 5xx both bounced a deep link to /home and
 *                  let the callback clear the flag this outcome exists to keep
 *                  (NUMA-142 P6 review).
 */
export type BootstrapOutcome = "redirected" | "done" | "retry"

export async function runIntegrationBootstrap(token: string): Promise<BootstrapOutcome> {
  const res = await fetch("/api/auth/bootstrap", {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
  })

  if (!res.ok) {
    // A 5xx or a network blip is not "bootstrapped". Clearing the flag here
    // meant one transient failure left the user's integrations permanently
    // un-bootstrapped, with no path back short of clearing storage
    // (NUMA-142 P6, PLAN 7). A 4xx is the caller's, so it does not repeat.
    if (res.status >= 500) return "retry"
    clearIntegrationBootstrapPending()
    return "done"
  }

  const data = (await res.json()) as BootstrapResponse
  const action = data.next_action

  if (
    action?.type === "oauth_redirect" &&
    isAllowedExternalUrl(action.authorization_url, OAUTH_AUTHORIZE_URL_PREFIXES)
  ) {
    const visited = getVisited()
    if (!visited.includes(action.service)) {
      setVisited([...visited, action.service])
      writeStorage(BOOTSTRAP_FLAG, "1")
      window.location.href = action.authorization_url
      return "redirected"
    }
  }

  clearIntegrationBootstrapPending()
  return "done"
}
