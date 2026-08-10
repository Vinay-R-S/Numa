"use client"

import { useRef } from "react"
import type { MouseEvent as ReactMouseEvent } from "react"

import { cn } from "@/lib/utils"
import {
  DRAG_SNAP_MINUTES,
  MAX_EVENT_END_MINUTES,
  MAX_EVENT_START_MINUTES,
  MIN_EVENT_DURATION_MINUTES,
  MIN_EVENT_START_MINUTES,
  SLOT_HEIGHT,
} from "../calendar.constants"
import { eventBlockGeometry } from "../calendar.utils"
import type { CalendarEvent } from "../calendar.types"

interface DayEventBlockProps {
  event: CalendarEvent
  onDragEnd: (id: string, newStartMin: number) => void
  onResizeEnd: (id: string, newEndMin: number) => void
  onHover: (event: CalendarEvent, mouseEvent: ReactMouseEvent<HTMLElement>) => void
  onHoverEnd: () => void
  onTap?: () => void
}

function snappedDelta(deltaY: number): number {
  return Math.round((deltaY / SLOT_HEIGHT) * 60 / DRAG_SNAP_MINUTES) * DRAG_SNAP_MINUTES
}

export function DayEventBlock({
  event,
  onDragEnd,
  onResizeEnd,
  onHover,
  onHoverEnd,
  onTap,
}: DayEventBlockProps) {
  const { startMinutes, endMinutes, top, height } = eventBlockGeometry(
    event.startTime,
    event.endTime,
    SLOT_HEIGHT
  )

  const pointerStartY = useRef(0)
  const isSecondary = event.color === "secondary"
  const isReadonly = event.readonly === true

  // Commit the new bounds on mouse-up; the in-flight feedback is hover styling.
  // A gesture that snaps to zero minutes is a plain click, not a drag: committing
  // it would push the event through the 7 AM / 8 PM clamps and silently
  // reschedule anything starting outside that window.
  const beginPointerGesture = (
    mouseEvent: ReactMouseEvent,
    commit: (deltaMinutes: number) => void
  ) => {
    if (isReadonly) return

    mouseEvent.stopPropagation()
    pointerStartY.current = mouseEvent.clientY

    const onUp = (upEvent: MouseEvent) => {
      globalThis.removeEventListener("mouseup", onUp)
      const deltaMinutes = snappedDelta(upEvent.clientY - pointerStartY.current)
      if (deltaMinutes === 0) return
      commit(deltaMinutes)
    }

    globalThis.addEventListener("mouseup", onUp)
  }

  const handleDragStart = (mouseEvent: ReactMouseEvent) => {
    beginPointerGesture(mouseEvent, (deltaMinutes) => {
      const newStart = Math.max(
        MIN_EVENT_START_MINUTES,
        Math.min(MAX_EVENT_START_MINUTES, startMinutes + deltaMinutes)
      )
      onDragEnd(event.id, newStart)
    })
  }

  const handleResizeStart = (mouseEvent: ReactMouseEvent) => {
    beginPointerGesture(mouseEvent, (deltaMinutes) => {
      const newEnd = Math.max(
        startMinutes + MIN_EVENT_DURATION_MINUTES,
        Math.min(MAX_EVENT_END_MINUTES, endMinutes + deltaMinutes)
      )
      onResizeEnd(event.id, newEnd)
    })
  }

  return (
    <div
      className={cn(
        "group absolute left-0.5 right-0.5 cursor-grab overflow-hidden rounded-md border-0 border-l-2 px-2 py-1 transition-all duration-150 active:cursor-grabbing sm:px-2.5 sm:py-1.5",
        isReadonly && "cursor-default",
        onTap && "cursor-pointer",
        "bg-white/[0.05] hover:bg-white/[0.08]",
        isSecondary ? "border-l-secondary/70" : "border-l-primary/70"
      )}
      style={{ top, height: Math.max(height, 24), zIndex: 10 }}
      onMouseDown={handleDragStart}
      onMouseEnter={(mouseEvent) => {
        mouseEvent.stopPropagation()
        onHover(event, mouseEvent)
      }}
      onMouseLeave={onHoverEnd}
      onClick={(mouseEvent) => {
        if (!onTap) return
        mouseEvent.stopPropagation()
        onTap()
      }}
    >
      <div className="truncate text-[11px] font-medium text-foreground sm:text-xs">{event.title}</div>
      {height >= 36 && (
        <div className="text-[9px] text-muted-foreground sm:text-[10px]">
          {event.startTime} - {event.endTime}
        </div>
      )}

      {!isReadonly && (
        <div
          className="absolute bottom-0 left-0 right-0 hidden h-2 cursor-s-resize items-center justify-center opacity-0 group-hover:flex group-hover:opacity-100"
          onMouseDown={handleResizeStart}
        >
          <div className="h-1 w-8 rounded-full bg-muted-foreground/30" />
        </div>
      )}
    </div>
  )
}
