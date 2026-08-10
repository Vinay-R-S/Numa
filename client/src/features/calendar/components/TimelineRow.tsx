"use client"

import { Clock, Droplets, UtensilsCrossed } from "lucide-react"

import { cn } from "@/lib/utils"
import { formatTime12 } from "../calendar.utils"
import type { TimelineItem, TimelineItemType } from "../calendar.types"

const DOT_COLORS: Record<TimelineItemType, string> = {
  calendar: "bg-sky-400/70",
  task: "bg-blue-400/70",
  meal: "bg-amber-400/70",
  water: "bg-cyan-400/70",
}

const RING_COLORS: Record<TimelineItemType, string> = {
  calendar: "ring-sky-400/40",
  task: "ring-blue-400/40",
  meal: "ring-amber-400/40",
  water: "ring-cyan-400/40",
}

function TimelineIcon({ type }: { type: TimelineItemType }) {
  if (type === "water") return <Droplets className="h-3 w-3 text-cyan-400/80" />
  if (type === "meal") return <UtensilsCrossed className="h-3 w-3 text-amber-400/80" />
  if (type === "task") return <Clock className="h-3 w-3 text-blue-400/80" />
  return null
}

export function TimelineNowRow({ now }: { now: string }) {
  return (
    <div className="relative flex items-center py-2 pl-10 pr-4">
      <div className="absolute bottom-0 left-[18px] top-0 w-px bg-border/30" />
      <div className="absolute left-[11px] top-1/2 z-10 h-3.5 w-3.5 -translate-y-1/2 rounded-full border-2 border-card bg-primary shadow-sm" />
      <div className="min-w-0 flex-1">
        <div className="h-px bg-primary/40" />
        <span className="mt-1 block text-[10px] font-medium text-primary">Now {formatTime12(now)}</span>
      </div>
    </div>
  )
}

export function TimelineItemRow({ item }: { item: TimelineItem }) {
  const isActive = item.state === "active"

  return (
    <div
      className={cn(
        "relative flex items-start py-2 pl-10 pr-4",
        item.state === "completed" && "opacity-50",
        isActive && "rounded-lg bg-primary/5"
      )}
    >
      <div className="absolute bottom-0 left-[18px] top-0 w-px bg-border/30" />

      <div
        className={cn(
          "absolute left-[14px] top-3 h-2.5 w-2.5 rounded-full",
          DOT_COLORS[item.type],
          isActive && "left-[13.5px] h-3 w-3 animate-pulse ring-2",
          isActive && RING_COLORS[item.type]
        )}
      />

      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-1.5">
          <TimelineIcon type={item.type} />
          <span
            className={cn(
              "truncate text-xs font-medium text-foreground",
              item.state === "completed" && "text-muted-foreground line-through"
            )}
          >
            {item.title}
          </span>
        </div>

        <div className="mt-0.5 flex items-center gap-1 text-[10px] text-muted-foreground">
          <span>{formatTime12(item.time)}</span>
          {item.endTime && (
            <>
              <span>-</span>
              <span>{formatTime12(item.endTime)}</span>
            </>
          )}
        </div>

        {item.description && (
          <p className="mt-0.5 truncate text-[10px] leading-tight text-muted-foreground/70">
            {item.description}
          </p>
        )}
      </div>
    </div>
  )
}
