"use client"

import { ChevronLeft, ChevronRight } from "lucide-react"

import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import type { ViewMode } from "../calendar.types"

interface CalendarToolbarProps {
  headerLabel: string
  view: ViewMode
  isMobile: boolean
  onChangeView: (mode: ViewMode) => void
  onNavigate: (direction: number) => void
  onToday: () => void
}

const VIEW_MODES: ViewMode[] = ["month", "week", "day"]

export function CalendarToolbar({
  headerLabel,
  view,
  isMobile,
  onChangeView,
  onNavigate,
  onToday,
}: CalendarToolbarProps) {
  return (
    <div className="mb-2 flex flex-col gap-2 sm:mb-4 sm:flex-row sm:items-center sm:justify-between">
      <h2 className="truncate text-lg font-bold text-foreground sm:text-2xl">{headerLabel}</h2>
      <div className="flex items-center gap-1 sm:gap-2">
        <div className="flex gap-0.5 rounded-md border border-border/40 bg-card p-0.5">
          {VIEW_MODES.map((mode) => (
            <button
              key={mode}
              onClick={(event) => {
                event.stopPropagation()
                onChangeView(mode)
              }}
              className={cn(
                "rounded-md px-2 py-1 text-xs font-medium capitalize transition-all sm:px-3 sm:py-1.5",
                view === mode
                  ? "bg-primary text-primary-foreground"
                  : "text-muted-foreground hover:bg-accent/40 hover:text-foreground"
              )}
            >
              {isMobile ? mode.charAt(0).toUpperCase() : mode}
            </button>
          ))}
        </div>
        <Button variant="ghost" size="icon" className="h-8 w-8 sm:h-9 sm:w-9" onClick={() => onNavigate(-1)}>
          <ChevronLeft className="h-4 w-4" />
        </Button>
        <Button
          variant="ghost"
          size="sm"
          className="h-8 px-2 text-xs sm:h-9 sm:px-3 sm:text-sm"
          onClick={onToday}
        >
          Today
        </Button>
        <Button variant="ghost" size="icon" className="h-8 w-8 sm:h-9 sm:w-9" onClick={() => onNavigate(1)}>
          <ChevronRight className="h-4 w-4" />
        </Button>
      </div>
    </div>
  )
}
