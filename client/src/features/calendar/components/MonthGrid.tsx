"use client"

import { useMemo } from "react"
import type { MouseEvent as ReactMouseEvent } from "react"

import { cn } from "@/lib/utils"
import { DAYS } from "../calendar.constants"
import { dayKey, getMonthGrid, groupEventsByDay, isSameDay, toDateParam } from "../calendar.utils"
import type { CalendarEvent } from "../calendar.types"
import { EventChip } from "./EventChip"

interface MonthGridProps {
  events: CalendarEvent[]
  currentDate: Date
  today: Date
  isMobile: boolean
  onOpenDay: (date: Date) => void
  onEventHover: (event: CalendarEvent, mouseEvent: ReactMouseEvent<HTMLElement>) => void
  onEventHoverEnd: () => void
  onEditEvent?: (event: CalendarEvent) => void
}

const noop = () => {}

export function MonthGrid({
  events,
  currentDate,
  today,
  isMobile,
  onOpenDay,
  onEventHover,
  onEventHoverEnd,
  onEditEvent,
}: MonthGridProps) {
  const cells = getMonthGrid(currentDate.getFullYear(), currentDate.getMonth())
  const eventsByDay = useMemo(() => groupEventsByDay(events), [events])
  const visibleCount = isMobile ? 1 : 2

  // Mobile has no hover: tapping an event opens the edit dialog instead.
  const hover = isMobile ? noop : onEventHover
  const hoverEnd = isMobile ? noop : onEventHoverEnd
  const tap = isMobile ? onEditEvent : undefined

  return (
    <div className="flex-1 overflow-auto rounded-lg border border-border/40 bg-card/40 p-1 sm:rounded-xl sm:p-2">
      <div className="mb-1 grid grid-cols-7">
        {DAYS.map((day) => (
          <div key={day} className="py-1 text-center text-[10px] font-medium text-muted-foreground sm:py-2 sm:text-xs">
            {isMobile ? day.charAt(0) : day}
          </div>
        ))}
      </div>
      <div className="grid flex-1 grid-cols-7 gap-px">
        {cells.map((date, index) => {
          const dayEvents = date ? eventsByDay.get(dayKey(date)) ?? [] : []
          const isToday = !!date && isSameDay(date, today)
          const hiddenCount = dayEvents.length - visibleCount

          return (
            <div
              key={date ? toDateParam(date) : `pad-${currentDate.getFullYear()}-${currentDate.getMonth()}-${index}`}
              className={cn(
                "min-h-12 rounded-md p-0.5 transition-all sm:min-h-20 sm:p-1.5",
                date ? "cursor-pointer hover:bg-accent/30" : "opacity-0",
                isToday && "bg-primary/10 ring-1 ring-primary/40"
              )}
              onClick={(mouseEvent) => {
                mouseEvent.stopPropagation()
                if (date) onOpenDay(date)
              }}
            >
              {date && (
                <>
                  <span
                    className={cn(
                      "text-[10px] font-medium sm:text-xs",
                      isToday ? "font-bold text-primary" : "text-muted-foreground"
                    )}
                  >
                    {date.getDate()}
                  </span>
                  <div className="mt-0.5 space-y-0.5">
                    {dayEvents.slice(0, visibleCount).map((event) => (
                      <EventChip
                        key={event.id}
                        event={event}
                        variant="month"
                        onHover={hover}
                        onHoverEnd={hoverEnd}
                        onTap={tap}
                      />
                    ))}
                    {hiddenCount > 0 && (
                      <span className="text-[8px] text-muted-foreground sm:text-[10px]">+{hiddenCount} more</span>
                    )}
                  </div>
                </>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
