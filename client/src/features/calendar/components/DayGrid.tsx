"use client"

import type { MouseEvent as ReactMouseEvent } from "react"

import { DAY_START_HOUR, HOURS, SLOT_HEIGHT } from "../calendar.constants"
import { eventsForDay, formatHour, isSameDay } from "../calendar.utils"
import type { CalendarEvent } from "../calendar.types"
import { DayEventBlock } from "./DayEventBlock"

interface DayGridProps {
  events: CalendarEvent[]
  currentDate: Date
  today: Date
  isMobile: boolean
  showNowLine: boolean
  nowTop: number
  onSlotClick: (date: Date, hour: number, mouseEvent: ReactMouseEvent) => void
  onEventHover: (event: CalendarEvent, mouseEvent: ReactMouseEvent<HTMLElement>) => void
  onEventHoverEnd: () => void
  onDragEnd: (id: string, newStartMin: number) => void
  onResizeEnd: (id: string, newEndMin: number) => void
  onEditEvent?: (event: CalendarEvent) => void
}

export function DayGrid({
  events,
  currentDate,
  today,
  isMobile,
  showNowLine,
  nowTop,
  onSlotClick,
  onEventHover,
  onEventHoverEnd,
  onDragEnd,
  onResizeEnd,
  onEditEvent,
}: DayGridProps) {
  const gridHeight = HOURS.length * SLOT_HEIGHT

  return (
    <div className="relative flex-1 overflow-auto rounded-lg border border-white/[0.06] bg-black p-0 sm:rounded-xl">
      <div className="grid grid-cols-[44px_1fr] sm:grid-cols-[52px_1fr]">
        <div className="relative" style={{ height: gridHeight }}>
          {HOURS.map((hour) => (
            <div
              key={hour}
              className="absolute w-full pr-2 text-right text-[9px] text-white/25 sm:text-[10px]"
              style={{ top: (hour - DAY_START_HOUR) * SLOT_HEIGHT - 7 }}
            >
              {formatHour(hour)}
            </div>
          ))}
        </div>

        <div className="relative border-l border-white/[0.06]" style={{ height: gridHeight }}>
          {HOURS.map((hour) => (
            <div
              key={hour}
              className="absolute left-0 right-0 cursor-pointer border-t border-white/[0.06] transition-colors hover:bg-white/[0.02]"
              style={{ top: (hour - DAY_START_HOUR) * SLOT_HEIGHT, height: SLOT_HEIGHT }}
              onClick={(mouseEvent) => onSlotClick(currentDate, hour, mouseEvent)}
            />
          ))}

          {showNowLine && isSameDay(currentDate, today) && (
            <div className="absolute left-0 right-0 z-20 flex items-center" style={{ top: nowTop }}>
              <div className="h-1.5 w-1.5 rounded-full bg-red-500" />
              <div className="h-px flex-1 bg-red-500/50" />
            </div>
          )}

          {eventsForDay(events, currentDate).map((event) => (
            <DayEventBlock
              key={event.id}
              event={event}
              onDragEnd={onDragEnd}
              onResizeEnd={onResizeEnd}
              onHover={onEventHover}
              onHoverEnd={onEventHoverEnd}
              onTap={isMobile ? () => onEditEvent?.(event) : undefined}
            />
          ))}
        </div>
      </div>
    </div>
  )
}
