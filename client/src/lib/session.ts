/**
 * Session token ownership (NUMA-126 P6, PLAN 7 / 8).
 *
 * One home for the `numa_token` JWT: read, store, clear, and the local expiry
 * check the protected layout needed. The key literal was repeated in seven
 * places, so "sign out" meant whatever each caller remembered to do.
 *
 * The expiry check is a local decode, not a server round trip. It answers the
 * only question the layout has to answer before rendering - is this token still
 * worth sending - without adding a request to every page load. Anything the
 * decode cannot see (a revoked token, a rotated JWT_SECRET) surfaces as the
 * first real 401, which `lib/http` turns into the same sign-out.
 */
const TOKEN_KEY = "numa_token"

/** Treat a token expiring within this window as already expired. */
const EXPIRY_SKEW_SECONDS = 30

export function getToken(): string | null {
  if (typeof window === "undefined") return null
  return localStorage.getItem(TOKEN_KEY)
}

export function storeToken(token: string): void {
  if (typeof window === "undefined") return
  localStorage.setItem(TOKEN_KEY, token)
}

export function clearToken(): void {
  if (typeof window === "undefined") return
  localStorage.removeItem(TOKEN_KEY)
}

/** `exp` from the JWT payload, or null if the token is not decodable. */
function decodeExpiry(token: string): number | null {
  const payload = token.split(".")[1]
  if (!payload) return null

  try {
    const base64 = payload.replace(/-/g, "+").replace(/_/g, "/")
    const padded = base64.padEnd(base64.length + ((4 - (base64.length % 4)) % 4), "=")
    // The payload carries an email and a display name, so decode it as UTF-8
    // rather than trusting atob's latin1 output.
    const bytes = Uint8Array.from(atob(padded), (char) => char.charCodeAt(0))
    const claims: unknown = JSON.parse(new TextDecoder().decode(bytes))

    if (!claims || typeof claims !== "object") return null
    const { exp } = claims as { exp?: unknown }
    return typeof exp === "number" ? exp : null
  } catch {
    return null
  }
}

/**
 * True when the token is past `exp`, or malformed enough that we cannot tell.
 * An undecodable token is one the backend would reject anyway, so treating it
 * as expired fails safe.
 */
export function isTokenExpired(token: string): boolean {
  const exp = decodeExpiry(token)
  if (exp === null) return true
  return exp - EXPIRY_SKEW_SECONDS <= Date.now() / 1000
}

/** A token that is present and not expired. */
export function hasValidToken(): boolean {
  const token = getToken()
  return token !== null && !isTokenExpired(token)
}

/**
 * Drop the dead session and send the user to sign in.
 *
 * A hard navigation rather than a router push: this is reachable from zustand
 * stores and plain modules, not just React, and the surviving page state is
 * worthless once the session is gone. Skipped when already on `/auth`, so a
 * failing request on the sign-in page cannot loop.
 */
export function endSession(): void {
  if (typeof window === "undefined") return

  clearToken()
  if (window.location.pathname.startsWith("/auth")) return
  window.location.replace("/auth")
}
