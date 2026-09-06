"use client"

/**
 * Day-timeline settings hook (NUMA-119 P5, PLAN 17.1 / 21.2).
 *
 * Owns the nine fields the settings page held for the timeline section. The
 * storage key, the payload shape and the defaults belong to the calendar
 * feature, which reads them in `useCalendar`; this is the writing half, so it
 * imports both from there rather than restating the contract.
 *
 * The nine `useState` calls became one form object hydrated from storage after
 * mount, the same shape `useCalendar` uses on the reading side: storage is not
 * readable during SSR, so the stored values land on the first client effect and
 * partial data still falls back to the defaults field by field.
 *
 * Clamping is unchanged: each numeric field is normalized on blur and again on
 * save, so a value typed and saved without leaving the field is still bounded.
 */
import { useCallback, useEffect, useState } from "react"

import { TIMELINE_SETTINGS_KEY } from "@/features/calendar/calendar.constants"
import { parseTimelineSettings } from "@/features/calendar/calendar.settings"
import type { TimelineSettings } from "@/features/calendar/calendar.types"
import {
  DEFAULT_TIMELINE_FORM,
  TIMELINE_SAVED_TIMEOUT_MS,
  WATER_END_BOUNDS,
  WATER_START_BOUNDS,
  WATER_STEP_BOUNDS,
} from "./settings.constants"
import type { Bounds, TimelineForm, WaterFieldKey } from "./settings.types"
import { clampToBounds } from "./settings.utils"

function readStoredForm(): TimelineForm {
  try {
    const raw = localStorage.getItem(TIMELINE_SETTINGS_KEY)
    if (!raw) return DEFAULT_TIMELINE_FORM

    // Validated, not cast: the same unchecked parse on the reading side is what
    // made a zero step hang the calendar tab (NUMA-142 P6).
    const stored = parseTimelineSettings(JSON.parse(raw))
    return {
      intervalMs: stored.updateIntervalMs || DEFAULT_TIMELINE_FORM.intervalMs,
      waterEnabled: stored.waterEnabled ?? DEFAULT_TIMELINE_FORM.waterEnabled,
      waterStart: String(stored.waterConfig?.startHour ?? DEFAULT_TIMELINE_FORM.waterStart),
      waterEnd: String(stored.waterConfig?.endHour ?? DEFAULT_TIMELINE_FORM.waterEnd),
      waterStep: String(stored.waterConfig?.stepMinutes ?? DEFAULT_TIMELINE_FORM.waterStep),
      breakfast: stored.mealTimes?.breakfast ?? DEFAULT_TIMELINE_FORM.breakfast,
      lunch: stored.mealTimes?.lunch ?? DEFAULT_TIMELINE_FORM.lunch,
      dinner: stored.mealTimes?.dinner ?? DEFAULT_TIMELINE_FORM.dinner,
    }
  } catch {
    return DEFAULT_TIMELINE_FORM
  }
}

export function useTimelineSettings() {
  const [form, setForm] = useState<TimelineForm>(DEFAULT_TIMELINE_FORM)
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    // Storage is unreadable during SSR, so hydrating in an effect is the only
    // option: a lazy initializer would render stored values the server HTML
    // does not have. `useCalendar` reads the same key the same way.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setForm(readStoredForm())
  }, [])

  const setField = useCallback(
    <K extends keyof TimelineForm>(key: K, value: TimelineForm[K]) => {
      setForm((prev) => ({ ...prev, [key]: value }))
    },
    []
  )

  const normalizeField = useCallback((key: WaterFieldKey, bounds: Bounds) => {
    setForm((prev) => ({ ...prev, [key]: String(clampToBounds(prev[key], bounds)) }))
  }, [])

  const save = useCallback(() => {
    const startHour = clampToBounds(form.waterStart, WATER_START_BOUNDS)
    const endHour = clampToBounds(form.waterEnd, WATER_END_BOUNDS)
    const stepMinutes = clampToBounds(form.waterStep, WATER_STEP_BOUNDS)

    const settings: TimelineSettings = {
      updateIntervalMs: form.intervalMs,
      waterEnabled: form.waterEnabled,
      waterConfig: { startHour, endHour, stepMinutes },
      mealTimes: { breakfast: form.breakfast, lunch: form.lunch, dinner: form.dinner },
    }
    localStorage.setItem(TIMELINE_SETTINGS_KEY, JSON.stringify(settings))

    setForm((prev) => ({
      ...prev,
      waterStart: String(startHour),
      waterEnd: String(endHour),
      waterStep: String(stepMinutes),
    }))

    setSaved(true)
    setTimeout(() => setSaved(false), TIMELINE_SAVED_TIMEOUT_MS)
  }, [form])

  return { form, saved, setField, normalizeField, save }
}

export type UseTimelineSettingsReturn = ReturnType<typeof useTimelineSettings>
