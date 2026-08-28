"use client"

import { MEAL_FIELDS } from "../settings.constants"
import type { UseTimelineSettingsReturn } from "../useTimelineSettings"

const FIELD_CLASS =
  "w-full rounded-lg border border-border/60 bg-background/60 px-2 py-1.5 text-sm text-foreground [color-scheme:dark] focus:outline-none focus:ring-1 focus:ring-primary/50 [&::-webkit-calendar-picker-indicator]:invert"

/** Breakfast/lunch/dinner markers the day timeline draws. */
export function MealTimeFields({ timeline }: { timeline: UseTimelineSettingsReturn }) {
  const { form, setField } = timeline

  return (
    <div>
      <label className="mb-2 block text-xs font-medium text-muted-foreground">Meal Times</label>
      <div className="grid grid-cols-3 gap-2">
        {MEAL_FIELDS.map((meal) => (
          <div key={meal.key}>
            <label className="mb-1 block text-[10px] text-muted-foreground">{meal.label}</label>
            <input
              type="time"
              value={form[meal.key]}
              onChange={(e) => setField(meal.key, e.target.value)}
              className={FIELD_CLASS}
            />
          </div>
        ))}
      </div>
    </div>
  )
}
