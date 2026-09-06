/**
 * Timeline settings storage: one validated reader for both sides (NUMA-142 P6).
 *
 * The key was parsed in two places and both cast the result straight to
 * `TimelineSettings` with no validation. A stored `waterConfig.stepMinutes` of
 * zero or below made `for (let m = start; m <= end; m += step)` in
 * `useDayTimeline` loop forever inside a `useMemo`, freezing the tab and growing
 * the item array until the browser ran out of memory. The settings UI clamps on
 * save, but nothing clamped on read, and localStorage is editable by anyone with
 * the console open (PLAN 7 / 22.2).
 *
 * Every field is validated independently: a bad one falls back to its default
 * rather than discarding the rest of the object.
 */
import {
  DEFAULT_MEAL_TIMES,
  DEFAULT_TIMELINE_INTERVAL_MS,
  DEFAULT_WATER_CONFIG,
  TIMELINE_SETTINGS_KEY,
} from "./calendar.constants"
import type { TimelineSettings } from "./calendar.types"

const MIN_INTERVAL_MS = 1_000
const MAX_INTERVAL_MS = 3_600_000
const MIN_STEP_MINUTES = 1
const MAX_STEP_MINUTES = 24 * 60
const MAX_HOUR = 24

const HHMM_PATTERN = /^([01]\d|2[0-3]):[0-5]\d$/

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value)
}

function boundedNumber(value: unknown, min: number, max: number): number | undefined {
  if (typeof value !== "number" || !Number.isFinite(value)) return undefined
  if (value < min || value > max) return undefined
  return value
}

function timeOfDay(value: unknown): string | undefined {
  if (typeof value !== "string" || !HHMM_PATTERN.test(value)) return undefined
  return value
}

function waterConfigOf(value: unknown): TimelineSettings["waterConfig"] {
  if (!isRecord(value)) return undefined

  const startHour = boundedNumber(value.startHour, 0, MAX_HOUR)
  const endHour = boundedNumber(value.endHour, 0, MAX_HOUR)
  const stepMinutes = boundedNumber(value.stepMinutes, MIN_STEP_MINUTES, MAX_STEP_MINUTES)

  return {
    startHour: startHour ?? DEFAULT_WATER_CONFIG.startHour,
    endHour: endHour ?? DEFAULT_WATER_CONFIG.endHour,
    stepMinutes: stepMinutes ?? DEFAULT_WATER_CONFIG.stepMinutes,
  }
}

function mealTimesOf(value: unknown): TimelineSettings["mealTimes"] {
  if (!isRecord(value)) return undefined

  return {
    breakfast: timeOfDay(value.breakfast) ?? DEFAULT_MEAL_TIMES.breakfast,
    lunch: timeOfDay(value.lunch) ?? DEFAULT_MEAL_TIMES.lunch,
    dinner: timeOfDay(value.dinner) ?? DEFAULT_MEAL_TIMES.dinner,
  }
}

/** Validate an already-parsed value into settings the timeline can loop over. */
export function parseTimelineSettings(value: unknown): TimelineSettings {
  if (!isRecord(value)) return {}

  const settings: TimelineSettings = {}

  const intervalMs = boundedNumber(value.updateIntervalMs, MIN_INTERVAL_MS, MAX_INTERVAL_MS)
  settings.updateIntervalMs = intervalMs ?? DEFAULT_TIMELINE_INTERVAL_MS

  if (typeof value.waterEnabled === "boolean") settings.waterEnabled = value.waterEnabled

  const waterConfig = waterConfigOf(value.waterConfig)
  if (waterConfig) settings.waterConfig = waterConfig

  const mealTimes = mealTimesOf(value.mealTimes)
  if (mealTimes) settings.mealTimes = mealTimes

  return settings
}

/** Read and validate the stored timeline settings. Never throws. */
export function readTimelineSettings(): TimelineSettings {
  try {
    const raw = localStorage.getItem(TIMELINE_SETTINGS_KEY)
    return raw ? parseTimelineSettings(JSON.parse(raw)) : {}
  } catch {
    return {}
  }
}
