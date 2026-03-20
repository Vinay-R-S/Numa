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
  const tomorrow = new Date(now)
  tomorrow.setDate(tomorrow.getDate() + 1)

  // Quick actions
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

  // Event-based suggestions
  const eventSuggestions: Suggestion[] = []

  // Get upcoming events
  const upcomingEvents = events
    .filter((e) => e.date >= now)
    .sort((a, b) => a.date.getTime() - b.date.getTime())
    .slice(0, 3)

  if (upcomingEvents.length > 0) {
    eventSuggestions.push({
      icon: <Zap className="h-3 w-3" />,
      label: `Reschedule ${upcomingEvents[0].title}`,
      query: `Reschedule "${upcomingEvents[0].title}" to tomorrow at 2 PM`,
      category: "event",
    })
  }

  // Time-based suggestions
  const timeSuggestions: Suggestion[] = [
    {
      icon: <Calendar className="h-3 w-3" />,
      label: "Check Monday's schedule",
      query: "What's on my calendar next Monday?",
      category: "time",
    },
    {
      icon: <Clock className="h-3 w-3" />,
      label: "Schedule 30min call",
      query: "Schedule a 30 minute call tomorrow afternoon",
      category: "time",
    },
  ]

  return [...quickActions, ...eventSuggestions, ...timeSuggestions]
}

export function AgentSuggestions({ events, onSelectSuggestion }: AgentSuggestionsProps) {
  const suggestions = getSmartSuggestions(events)

  return (
    <div className="mb-3 space-y-2">
      <p className="text-xs font-medium text-muted-foreground">Quick Actions</p>
      <div className="grid grid-cols-1 gap-1.5">
        {suggestions.slice(0, 6).map((suggestion, index) => (
          <button
            key={index}
            onClick={() => onSelectSuggestion(suggestion.query)}
            className="group flex items-center gap-2 rounded-lg border border-border/30 bg-muted/20 px-3 py-2 text-left text-xs transition-all hover:border-primary/40 hover:bg-primary/5"
          >
            <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-md bg-primary/10 text-primary transition-colors group-hover:bg-primary/20">
              {suggestion.icon}
            </div>
            <span className="flex-1 truncate text-foreground">{suggestion.label}</span>
          </button>
        ))}
      </div>
    </div>
  )
}
