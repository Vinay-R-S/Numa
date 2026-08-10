/**
 * Dashboard pure helpers (NUMA-113 P4, PLAN 17.3).
 *
 * Extracted verbatim from `home/page.tsx` so formatting stays out of the
 * render path and can be unit tested.
 */

/** 1234 -> "1.2k", 850 -> "850". */
export function formatCompactValue(value: number): string {
  if (value >= 1000) return `${(value / 1000).toFixed(1)}k`
  return Math.round(value).toLocaleString()
}

/** Tooltip label for a weekly-activity series value. */
export function formatWeeklyMetric(value: number, metric: string | number): string {
  if (metric === "distance_km") return `${value.toFixed(1)} km`
  if (metric === "calories") return `${Math.round(value).toLocaleString()} kcal`
  return `${formatCompactValue(value)} steps`
}

export function isAbortError(error: unknown): boolean {
  return error instanceof DOMException && error.name === "AbortError"
}
