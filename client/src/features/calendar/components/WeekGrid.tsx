"use client"

import { useMemo } from "react"
import type { MouseEvent as ReactMouseEvent } from "react"

import { cn } from "@/lib/utils"
import { DAYS, HOURS } from "../calendar.constants"
import { dayKey, formatHour, getWeekDates, groupEventsByDay, isSameDay, toDateParam } from "../calendar.utils"
import type { CalendarEvent } from "../calendar.types"
import { EventChip } from "./EventChip"

interface WeekGridProps {
  events: CalendarEvent[]
  currentDate: Date
  today: Date
  isMobile: boolean
  onSlotClick: (date: Date, hour: number, mouseEvent: ReactMouseEvent) => void
  onEventHover: (event: CalendarEvent, mouseEvent: ReactMouseEvent<HTMLElement>) => void
  onEventHoverEnd: () => void
  onEditEvent?: (event: CalendarEvent) => void
}

const noop = () => {}

export function WeekGrid({
  events,
  currentDate,
  today,
  isMobile,
  onSlotClick,
  onEventHover,
  onEventHoverEnd,
  onEditEvent,
}: WeekGridProps) {
  const weekDates = getWeekDates(currentDate)
  // 105 cells: index once instead of filtering the whole month per cell.
  const eventsByDay = useMemo(() => groupEventsByDay(events), [events])

  const hover = isMobile ? noop : onEventHover
  const hoverEnd = isMobile ? noop : onEventHoverEnd
  const tap = isMobile ? onEditEvent : undefined

  return (
    <div className="flex-1 overflow-auto rounded-lg border border-border/40 bg-card/40 p-1 sm:rounded-xl sm:p-2">
      <div className="grid min-w-[500px] grid-cols-[40px_repeat(7,1fr)] gap-px sm:grid-cols-[50px_repeat(7,1fr)]">
        <div />
        {weekDates.map((date) => (
          <div
            key={toDateParam(date)}
            className={cn(
              "py-1 text-center text-[10px] font-medium sm:py-2 sm:text-xs",
              isSameDay(date, today) ? "text-primary" : "text-muted-foreground"
            )}
          >
            <div>{isMobile ? DAYS[date.getDay()].charAt(0) : DAYS[date.getDay()]}</div>
            <div
              className={cn(
                "text-sm font-bold sm:text-lg",
                isSameDay(date, today) ? "text-primary" : "text-foreground"
              )}
            >
              {date.getDate()}
            </div>
          </div>
        ))}

        {HOURS.map((hour) => (
          <div key={`row-${hour}`} className="contents">
            <div className="pr-1 pt-1 text-right text-[8px] text-muted-foreground sm:pr-2 sm:text-[10px]">
              {formatHour(hour)}
            </div>
            {weekDates.map((date) => (
              <div
                key={`${hour}-${toDateParam(date)}`}
                className="relative min-h-10 cursor-pointer border-t border-border/20 p-0.5 transition-colors hover:bg-accent/10 sm:min-h-12"
                onClick={(mouseEvent) => onSlotClick(date, hour, mouseEvent)}
              >
                {(eventsByDay.get(dayKey(date)) ?? [])
                  .filter((event) => parseInt(event.startTime, 10) === hour)
                  .map((event) => (
                    <EventChip
                      key={event.id}
                      event={event}
                      variant="week"
                      onHover={hover}
                      onHoverEnd={hoverEnd}
                      onTap={tap}
                    />
                  ))}
              </div>
            ))}
          </div>
        ))}
      </div>
    </div>
  )
}
