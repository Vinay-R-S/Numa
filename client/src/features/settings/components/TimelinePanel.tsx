"use client"

import { ChevronDown, Save, Timer } from "lucide-react"

import { Button } from "@/components/ui/button"

import { TIMELINE_INTERVAL_OPTIONS } from "../settings.constants"
import type { UseTimelineSettingsReturn } from "../useTimelineSettings"
import { MealTimeFields } from "./MealTimeFields"
import { SettingsSection } from "./SettingsSection"
import { WaterReminderFields } from "./WaterReminderFields"

/** Writes `numa_timeline_settings`, which the calendar page reads on mount. */
export function TimelinePanel({ timeline }: { timeline: UseTimelineSettingsReturn }) {
  return (
    <SettingsSection
      icon={Timer}
      title="Timeline Settings"
      description="Configure the day timeline on the Calendar page: update frequency, water reminders, and meal times."
    >
      <div className="space-y-4 rounded-xl border border-border/40 bg-background/40 p-3 sm:p-4">
        <div>
          <label className="mb-1.5 block text-xs font-medium text-muted-foreground">
            Update Interval
          </label>
          <div className="relative">
            <select
              value={timeline.form.intervalMs}
              onChange={(e) => timeline.setField("intervalMs", Number(e.target.value))}
              className="h-11 w-full appearance-none rounded-lg border border-border/60 bg-background/60 px-3 pr-10 text-sm text-foreground [color-scheme:dark] focus:outline-none focus:ring-1 focus:ring-primary/50"
            >
              {TIMELINE_INTERVAL_OPTIONS.map((option) => (
                <option
                  key={option.value}
                  className="bg-popover text-popover-foreground"
                  value={option.value}
                >
                  {option.label}
                </option>
              ))}
            </select>
            <ChevronDown className="pointer-events-none absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          </div>
        </div>

        <WaterReminderFields timeline={timeline} />

        <MealTimeFields timeline={timeline} />

        <div className="flex items-center gap-2">
          <Button type="button" size="sm" className="gap-1.5" onClick={timeline.save}>
            <Save className="h-3.5 w-3.5" />
            Save Timeline Settings
          </Button>
          {timeline.saved && <span className="text-xs text-emerald-400">Saved!</span>}
        </div>
      </div>
    </SettingsSection>
  )
}
