"use client"

import { CalendarDays, Clock } from "lucide-react"
import { cn } from "@/lib/utils"
import { ICON_COLORS } from "../dashboard.constants"
import type { DashboardUpcomingEvent } from "../dashboard.types"

const MAX_EVENTS = 5

export function UpcomingEventsCard({ events }: { events: DashboardUpcomingEvent[] }) {
  return (
    <div className="rounded-xl border border-border/40 bg-card/40 p-4">
      <div className="mb-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <CalendarDays className={cn("h-4 w-4", ICON_COLORS.calendar)} />
          <span className="text-sm font-semibold text-foreground">Upcoming Events</span>
        </div>
        <a href="/calendar" className="text-xs text-muted-foreground hover:text-foreground">
          View all
        </a>
      </div>
      {events.length === 0 ? (
        <p className="text-xs text-muted-foreground py-4 text-center">No upcoming events</p>
      ) : (
        <div className="space-y-2">
          {events.slice(0, MAX_EVENTS).map((event) => (
            <div
              key={`${event.start_at}-${event.title}`}
              className="flex items-center gap-3 rounded-lg bg-background/40 px-3 py-2"
            >
              <Clock className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
              <div className="min-w-0 flex-1">
                <p className="truncate text-xs font-medium text-foreground">{event.title}</p>
                <p className="text-[10px] text-muted-foreground">
                  {new Date(event.start_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                </p>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
