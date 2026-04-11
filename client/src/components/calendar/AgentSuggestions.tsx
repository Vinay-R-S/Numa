"use client"

import { Clock, Calendar, Zap, Plus } from "lucide-react"
import { CalendarEvent } from "@/components/calendar/api"

interface Suggestion {
  icon: React.ReactNode
  label: string
  query: string
  category: "quick" | "event" | "time"
}

interface AgentSuggestionsProps {
  events: CalendarEvent[]
  onSelectSuggestion: (query: string) => void
}

function getSmartSuggestions(events: CalendarEvent[]): Suggestion[] {
  const now = new Date()

  const quickActions: Suggestion[] = [
    {
      icon: <Plus className="h-3 w-3" />,
      label: "Schedule meeting tomorrow at 10 AM",
      query: "Schedule a meeting tomorrow at 10 AM for 1 hour",
      category: "quick",
    },
    {
      icon: <Calendar className="h-3 w-3" />,
      label: "Show this week's events",
      query: "Show me all events this week",
      category: "quick",
    },
    {
      icon: <Clock className="h-3 w-3" />,
      label: "Find free slots today",
      query: "Find my free time slots today",
      category: "quick",
    },
  ]

  const upcomingEvents = events
    .filter((e) => e.date >= now)
    .sort((a, b) => a.date.getTime() - b.date.getTime())
    .slice(0, 1)

  if (upcomingEvents.length > 0) {
    quickActions.push({
      icon: <Zap className="h-3 w-3" />,
      label: `Reschedule ${upcomingEvents[0].title}`,
      query: `Reschedule "${upcomingEvents[0].title}" to tomorrow at 2 PM`,
      category: "event",
    })
  }

  return quickActions
}

export function AgentSuggestions({ events, onSelectSuggestion }: AgentSuggestionsProps) {
  const suggestions = getSmartSuggestions(events)

  return (
    <div className="mb-2">
      <p className="mb-1.5 text-[10px] font-medium uppercase tracking-wider text-muted-foreground/60">
        Quick Actions
      </p>
      <div className="flex flex-wrap gap-1.5">
        {suggestions.slice(0, 4).map((suggestion, index) => (
          <button
            key={index}
            onClick={() => onSelectSuggestion(suggestion.query)}
            className="flex items-center gap-1.5 rounded-full border border-border/30 bg-muted/20 px-2.5 py-1 text-[11px] text-foreground/80 transition-all hover:border-primary/40 hover:bg-primary/5 hover:text-foreground"
          >
            <span className="text-primary">{suggestion.icon}</span>
            <span className="truncate max-w-[150px]">{suggestion.label}</span>
          </button>
        ))}
      </div>
    </div>
  )
}
