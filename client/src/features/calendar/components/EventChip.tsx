"use client"

import type { MouseEvent as ReactMouseEvent } from "react"

import { cn } from "@/lib/utils"
import type { CalendarEvent } from "../calendar.types"

interface EventChipProps {
  event: CalendarEvent
  variant: "month" | "week"
  onHover: (event: CalendarEvent, mouseEvent: ReactMouseEvent<HTMLElement>) => void
  onHoverEnd: () => void
  onTap?: (event: CalendarEvent) => void
}

const VARIANT_CLASSES = {
  month: "truncate rounded border px-1 py-0.5 text-[8px] font-medium transition-all hover:-translate-y-px sm:px-1.5 sm:text-[10px]",
  week: "cursor-pointer rounded border px-1 py-0.5 text-[8px] font-medium transition-all hover:-translate-y-px sm:px-1.5 sm:py-1 sm:text-[10px]",
}

/** Compact event chip used by the month and week grids. */
export function EventChip({ event, variant, onHover, onHoverEnd, onTap }: EventChipProps) {
  return (
    <div
      onMouseEnter={(mouseEvent) => onHover(event, mouseEvent)}
      onMouseLeave={onHoverEnd}
      onClick={(mouseEvent) => {
        mouseEvent.stopPropagation()
        onTap?.(event)
      }}
      className={cn(
        VARIANT_CLASSES[variant],
        event.color === "secondary"
          ? "border-secondary/25 bg-secondary/15"
          : "border-primary/25 bg-primary/15"
      )}
    >
      {variant === "week" ? (
        <>
          <div className="truncate">{event.title}</div>
          <div className="hidden text-muted-foreground sm:block">{event.startTime}</div>
        </>
      ) : (
        event.title
      )}
    </div>
  )
}
