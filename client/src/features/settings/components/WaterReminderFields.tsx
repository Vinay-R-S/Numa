"use client"

import { cn } from "@/lib/utils"

import { WATER_END_BOUNDS, WATER_START_BOUNDS, WATER_STEP_BOUNDS } from "../settings.constants"
import type { Bounds, WaterFieldKey } from "../settings.types"
import type { UseTimelineSettingsReturn } from "../useTimelineSettings"

const FIELD_CLASS =
  "w-full rounded-lg border border-border/60 bg-background/60 px-2 py-1.5 text-sm text-foreground [appearance:textfield] [color-scheme:dark] focus:outline-none focus:ring-1 focus:ring-primary/50 [&::-webkit-inner-spin-button]:appearance-none [&::-webkit-outer-spin-button]:appearance-none"

const WATER_FIELDS: { key: WaterFieldKey; label: string; bounds: Bounds }[] = [
  { key: "waterStart", label: "Start Hour", bounds: WATER_START_BOUNDS },
  { key: "waterEnd", label: "End Hour", bounds: WATER_END_BOUNDS },
  { key: "waterStep", label: "Step (min)", bounds: WATER_STEP_BOUNDS },
]

/**
 * Water reminder switch and its window. The three inputs stay text rather than
 * number so a half-typed value is not swallowed by the browser; each one is
 * clamped on blur.
 */
export function WaterReminderFields({ timeline }: { timeline: UseTimelineSettingsReturn }) {
  const { form, setField, normalizeField } = timeline

  return (
    <div>
      <div className="mb-2 flex items-center justify-between">
        <label className="text-xs font-medium text-muted-foreground">Water Reminders</label>
        <button
          type="button"
          onClick={() => setField("waterEnabled", !form.waterEnabled)}
          className="relative inline-flex h-5 w-9 shrink-0 items-center rounded-full border border-border/70 bg-background/70 transition-colors"
        >
          <span
            className={cn(
              "inline-block h-3.5 w-3.5 rounded-full transition-transform",
              form.waterEnabled ? "bg-emerald-400" : "bg-white",
              form.waterEnabled ? "translate-x-[18px]" : "translate-x-[3px]"
            )}
          />
        </button>
      </div>

      {form.waterEnabled && (
        <div className="grid grid-cols-3 gap-2">
          {WATER_FIELDS.map((field) => (
            <div key={field.key}>
              <label className="mb-1 block text-[10px] text-muted-foreground">{field.label}</label>
              <input
                type="text"
                inputMode="numeric"
                value={form[field.key]}
                onChange={(e) => setField(field.key, e.target.value)}
                onBlur={() => normalizeField(field.key, field.bounds)}
                className={FIELD_CLASS}
              />
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
