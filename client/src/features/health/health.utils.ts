/**
 * Health pure helpers (NUMA-116 P4, PLAN 17.2).
 *
 * Number/date formatting and the sleep-segment normalizer, lifted verbatim from
 * `health/page.tsx`. No React, no fetching.
 */
import { SLEEP_STAGE_META } from "./health.constants"
import type { SleepStage, SleepTimelineSegment } from "./health.types"

export function formatNumber(n: number | null | undefined): string {
  if (n == null) return "-"
  return n >= 1000 ? n.toLocaleString() : String(Math.round(n * 10) / 10)
}

export function pct(value: number | null, goal: number): number {
  if (!value) return 0
  return Math.min(100, Math.round((value / goal) * 100))
}

export function localDateString(date = new Date()): string {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, "0")
  const day = String(date.getDate()).padStart(2, "0")
  return `${year}-${month}-${day}`
}

/**
 * A metric value with its unit. Named apart from `dashboard.utils`'s
 * `formatCompactValue`, which takes no unit: one name covered two incompatible
 * functions (NUMA-142 P6, PLAN 10).
 */
export function formatMetricValue(value: number, unit: string): string {
  if (unit === "km") return `${value.toFixed(1)} km`
  if (value >= 1000) return `${(value / 1000).toFixed(1)}k`
  return `${Math.round(value).toLocaleString()}`
}

/**
 * The seven days ending on `anchor` (today by default). Callers that memoize the
 * result pass the anchor explicitly so the window is part of their cache key.
 */
export function lastSevenDays(anchor: Date = new Date()): Date[] {
  return Array.from({ length: 7 }, (_, index) => {
    const date = new Date(anchor)
    date.setDate(date.getDate() - (6 - index))
    return date
  })
}

export function formatDateLabel(dateKey: string): string {
  const today = localDateString()
  const yesterdayDate = new Date()
  yesterdayDate.setDate(yesterdayDate.getDate() - 1)
  const yesterday = localDateString(yesterdayDate)

  if (dateKey === today) return "Today"
  if (dateKey === yesterday) return "Yesterday"

  const parsed = new Date(`${dateKey}T00:00:00`)
  return parsed.toLocaleDateString([], { month: "short", day: "numeric" })
}

export function readNumber(value: unknown): number | null {
  if (typeof value === "number" && Number.isFinite(value)) return value
  if (typeof value === "string" && value.trim()) {
    const parsed = Number(value)
    return Number.isFinite(parsed) ? parsed : null
  }
  return null
}

export function normalizeSleepStage(value: unknown): SleepStage {
  const stage = typeof value === "string" ? value.toLowerCase() : "generic"
  return stage === "light" || stage === "deep" || stage === "rem" ? stage : "generic"
}

export function formatSleepDuration(hours: number): string {
  const safeHours = Math.max(0, hours)
  const wholeHours = Math.floor(safeHours)
  const minutes = Math.round((safeHours - wholeHours) * 60)
  if (minutes === 60) return `${wholeHours + 1}h 0m`
  return `${wholeHours}h ${minutes}m`
}

export function formatSleepTime(ms: number | null): string {
  if (!ms) return "-"
  return new Date(ms).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
}

export function parseSleepTimestamp(value: string | null | undefined): number | null {
  if (!value) return null
  const parsed = new Date(value).getTime()
  return Number.isFinite(parsed) ? parsed : null
}

/**
 * Flattens overlapping synced sleep segments into a single ordered timeline:
 * every boundary becomes a slice, the deepest stage covering a slice wins, and
 * adjacent slices of the same stage merge.
 */
export function normalizeSleepSegments(
  rawSegments: Array<Record<string, unknown>> | null | undefined
): SleepTimelineSegment[] {
  const segments = (rawSegments || [])
    .map((segment) => {
      const startMs = readNumber(segment.start_ms)
      const endMs = readNumber(segment.end_ms)
      if (startMs == null || endMs == null || endMs <= startMs) return null
      return {
        startMs,
        endMs,
        stage: normalizeSleepStage(segment.stage),
      }
    })
    .filter((segment): segment is { startMs: number; endMs: number; stage: SleepStage } =>
      Boolean(segment)
    )

  if (segments.length === 0) return []

  const boundaries = Array.from(
    new Set(segments.flatMap((segment) => [segment.startMs, segment.endMs]))
  ).sort((a, b) => a - b)
  const normalized: SleepTimelineSegment[] = []

  for (let index = 0; index < boundaries.length - 1; index += 1) {
    const startMs = boundaries[index]
    const endMs = boundaries[index + 1]
    const covering = segments.filter(
      (segment) => segment.startMs < endMs && segment.endMs > startMs
    )
    if (covering.length === 0) continue
    const chosen = covering.reduce((best, segment) =>
      SLEEP_STAGE_META[segment.stage].priority > SLEEP_STAGE_META[best.stage].priority
        ? segment
        : best
    )
    const previous = normalized[normalized.length - 1]
    if (previous && previous.stage === chosen.stage && previous.endMs === startMs) {
      previous.endMs = endMs
      previous.hours = (previous.endMs - previous.startMs) / (1000 * 60 * 60)
    } else {
      normalized.push({
        startMs,
        endMs,
        stage: chosen.stage,
        hours: (endMs - startMs) / (1000 * 60 * 60),
      })
    }
  }

  return normalized
}
