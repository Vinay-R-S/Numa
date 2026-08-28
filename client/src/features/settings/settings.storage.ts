/**
 * Client-side settings storage (NUMA-119 P5, PLAN 21.2).
 *
 * Deliberately dependency-free: `calendar.api.ts` and `masterAgent.api.ts` read
 * the agent kill switch on every agent call, so anything imported here lands in
 * their bundles. The rest of the feature's helpers live in `settings.utils.ts`,
 * which pulls in icons and constants.
 */

/** Local-only agent kill switch, written by the settings page. */
export const AI_ENABLED_STORAGE_KEY = "numa_ai_enabled"

/** Defaults to enabled when never set. */
export function getLocalAiEnabled(): boolean {
  if (typeof globalThis.localStorage === "undefined") return true
  const raw = localStorage.getItem(AI_ENABLED_STORAGE_KEY)
  return raw === null ? true : raw === "true"
}

export function setLocalAiEnabled(enabled: boolean): void {
  if (typeof globalThis.localStorage === "undefined") return
  localStorage.setItem(AI_ENABLED_STORAGE_KEY, String(enabled))
}
