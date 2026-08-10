"use client"

import { useLayoutEffect, useRef, useState } from "react"
import { Clock, X } from "lucide-react"

import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import { detailPopupPosition } from "../calendar.utils"
import type { AnchorRect, CalendarEvent } from "../calendar.types"

interface EventDetailPopupProps {
  event: CalendarEvent
  anchorRect: AnchorRect
  onEdit?: (event: CalendarEvent) => void
  onDelete: (eventId: string) => Promise<void>
  onHoverStart: () => void
  onHoverEnd: () => void
  onClose: () => void
}

export function EventDetailPopup({
  event,
  anchorRect,
  onEdit,
  onDelete,
  onHoverStart,
  onHoverEnd,
  onClose,
}: EventDetailPopupProps) {
  const popupRef = useRef<HTMLDivElement>(null)
  const [coords, setCoords] = useState({ left: -9999, top: -9999 })

  useLayoutEffect(() => {
    const popup = popupRef.current
    if (!popup) return

    const rect = popup.getBoundingClientRect()
    const { x, y } = detailPopupPosition(
      anchorRect,
      { width: rect.width, height: rect.height },
      { width: globalThis.innerWidth, height: globalThis.innerHeight }
    )
    setCoords({ left: x, top: y })
  }, [anchorRect, event.id])

  const isSecondary = event.color === "secondary"

  return (
    <div
      ref={popupRef}
      className="fixed z-200"
      style={{ top: coords.top, left: coords.left }}
      onMouseEnter={onHoverStart}
      onMouseLeave={onHoverEnd}
    >
      <div className="w-72 rounded-xl border border-border/30 bg-card/95 p-4 shadow-lg backdrop-blur-md">
        <div className="mb-3 flex items-start justify-between">
          <div className={cn("h-1 w-10 rounded-full", isSecondary ? "bg-secondary" : "bg-primary")} />
          <button onClick={onClose} className="text-muted-foreground transition-colors hover:text-foreground">
            <X className="h-4 w-4" />
          </button>
        </div>
        <h3 className="mb-2 text-sm font-semibold text-foreground">{event.title}</h3>
        {event.calendarName && (
          <div className="mb-1 text-[11px] text-muted-foreground">Calendar: {event.calendarName}</div>
        )}
        <div className="mb-2 flex items-center gap-1.5 text-xs text-muted-foreground">
          <Clock className="h-3 w-3" />
          <span>
            {event.startTime} - {event.endTime}
          </span>
        </div>
        <p className="text-xs leading-relaxed text-muted-foreground/80">{event.description}</p>
        {!event.readonly && (
          <div className="mt-3 flex gap-2">
            <Button
              variant="outline"
              size="sm"
              className="flex-1"
              onClick={() => {
                onEdit?.(event)
                onClose()
              }}
            >
              Edit
            </Button>
            <Button
              variant="destructive"
              size="sm"
              className="flex-1"
              onClick={async () => {
                await onDelete(event.id)
                onClose()
              }}
            >
              Delete
            </Button>
          </div>
        )}
      </div>
    </div>
  )
}
