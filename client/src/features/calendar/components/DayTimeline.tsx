"use client"

import { CalendarDays } from "lucide-react"

import { useDayTimeline } from "../useDayTimeline"
import type { CalendarEvent, TimelineSettings } from "../calendar.types"
import { TimelineItemRow, TimelineNowRow } from "./TimelineRow"

export interface DayTimelineProps {
  calendarEvents: CalendarEvent[]
  updateIntervalMs?: number
  waterConfig?: TimelineSettings["waterConfig"]
  mealTimes?: TimelineSettings["mealTimes"]
}

/** Today's merged agenda rail: calendar events, due tasks, meals and water. */
export function DayTimeline({ calendarEvents, updateIntervalMs, waterConfig, mealTimes }: DayTimelineProps) {
  const { now, dateLabel, rows, isEmpty, totalEvents, completedCount } = useDayTimeline({
    calendarEvents,
    updateIntervalMs,
    waterConfig,
    mealTimes,
  })

  return (
    <div className="flex h-full flex-col overflow-hidden rounded-xl border border-border/40 bg-card/40">
      <div className="shrink-0 border-b border-border/30 px-4 py-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <CalendarDays className="h-4 w-4 text-primary" />
            <h3 className="text-sm font-semibold text-foreground">Today</h3>
          </div>
          <span className="rounded-full bg-primary/10 px-2 py-0.5 text-[10px] font-medium text-primary">
            {completedCount}/{totalEvents}
          </span>
        </div>
        <p className="mt-0.5 text-[11px] text-muted-foreground">{dateLabel}</p>
      </div>

      <div className="relative min-h-0 flex-1 overflow-y-auto py-3">
        {rows.map((row) =>
          row.kind === "now" ? (
            <TimelineNowRow key="timeline-now" now={now} />
          ) : (
            <TimelineItemRow key={row.item.id} item={row.item} />
          )
        )}

        {isEmpty && <p className="py-8 text-center text-xs text-muted-foreground">No events for today</p>}
      </div>
    </div>
  )
}
