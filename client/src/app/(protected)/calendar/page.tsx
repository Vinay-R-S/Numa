"use client"

import { useCallback, useEffect, useMemo, useRef, useState } from "react"
import { CalendarDays, Search } from "lucide-react"

import CalendarView from "@/components/calendar/CalendarView"
import { Button } from "@/components/ui/button"
import {
  AgentChatMessage,
  CalendarEvent,
  CalendarEventPayload,
  createCalendarEvent,
  deleteCalendarEvent,
  fetchCalendarEvents,
  getGoogleCalendarAuthorizationUrl,
  sendAgentCommand,
  startCalendarWatch,
  subscribeToCalendarUpdates,
  updateCalendarEvent,
} from "@/components/calendar/api"

export default function CalendarPage() {
  const [events, setEvents] = useState<CalendarEvent[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [connectingGoogle, setConnectingGoogle] = useState(false)
  const [searchQuery, setSearchQuery] = useState("")
  const [agentMessages, setAgentMessages] = useState<AgentChatMessage[]>([
    {
      role: "assistant",
      content: "I am your Calendar sub-agent. Ask me to create, move, or cancel meetings.",
    },
  ])
  const [agentInput, setAgentInput] = useState("")
  const [agentSending, setAgentSending] = useState(false)
  const [agentError, setAgentError] = useState<string | null>(null)
  const watchInitAttempted = useRef(false)

  const loadEvents = useCallback(async () => {
    try {
      setError(null)
      const data = await fetchCalendarEvents()
      setEvents(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load calendar events")
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadEvents()
  }, [loadEvents])

  useEffect(() => {
    const unsubscribe = subscribeToCalendarUpdates(() => {
      loadEvents()
    })

    return unsubscribe
  }, [loadEvents])

  useEffect(() => {
    if (watchInitAttempted.current) {
      return
    }

    watchInitAttempted.current = true
    startCalendarWatch().catch((err) => {
      console.error("Failed to initialize calendar watch", err)
      watchInitAttempted.current = false
    })
  }, [])

  const handleCreateEvent = useCallback(
    async (payload: CalendarEventPayload) => {
      await createCalendarEvent(payload)
      await loadEvents()
    },
    [loadEvents]
  )

  const handleUpdateEvent = useCallback(
    async (event: CalendarEvent) => {
      const payload: CalendarEventPayload = {
        title: event.title,
        date: event.date.toISOString().slice(0, 10),
        startTime: event.startTime,
        endTime: event.endTime,
        description: event.description,
      }
      await updateCalendarEvent(event.id, payload)
      await loadEvents()
    },
    [loadEvents]
  )

  const handleDeleteEvent = useCallback(
    async (eventId: string) => {
      await deleteCalendarEvent(eventId)
      await loadEvents()
    },
    [loadEvents]
  )

  const handleConnectGoogleCalendar = useCallback(async () => {
    setConnectingGoogle(true)
    try {
      const authorizationUrl = await getGoogleCalendarAuthorizationUrl()
      window.location.assign(authorizationUrl)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to start Google authorization")
      setConnectingGoogle(false)
    }
  }, [])

  const calendarNotConnected =
    !!error &&
    (error.toLowerCase().includes("not connected") ||
      error.toLowerCase().includes("oauth/start") ||
      error.toLowerCase().includes("google oauth"))

  const handleSendAgentMessage = useCallback(async () => {
    const query = agentInput.trim()
    if (!query || agentSending) {
      return
    }

    const nextHistory: AgentChatMessage[] = [...agentMessages, { role: "user", content: query }]
    setAgentMessages(nextHistory)
    setAgentInput("")
    setAgentSending(true)
    setAgentError(null)

    try {
      const result = await sendAgentCommand(query, nextHistory)
      setAgentMessages((prev) => [...prev, { role: "assistant", content: result.response }])

      if (result.refreshCalendar) {
        await loadEvents()
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : "Calendar sub-agent request failed"
      setAgentError(message)
      setAgentMessages((prev) => [
        ...prev,
        { role: "assistant", content: `I hit an error: ${message}` },
      ])
    } finally {
      setAgentSending(false)
    }
  }, [agentInput, agentSending, agentMessages, loadEvents])

  const filteredEvents = useMemo(() => {
    if (!searchQuery.trim()) {
      return events
    }

    const q = searchQuery.toLowerCase()
    return events.filter(
      (event) =>
        event.title.toLowerCase().includes(q) ||
        event.description.toLowerCase().includes(q) ||
        (event.calendarName ?? "").toLowerCase().includes(q)
    )
  }, [events, searchQuery])

  return (
    <div className="mx-auto flex min-h-full w-full max-w-450 flex-col gap-6 px-6 py-6">
      <header className="flex items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary/10 ring-1 ring-primary/20">
            <CalendarDays className="h-5 w-5 text-primary" />
          </div>
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-foreground">Calendar</h1>
            <p className="text-sm text-muted-foreground">
              Manage Google Calendar events directly from NUMA
            </p>
          </div>
        </div>

        <div className="relative w-full max-w-xs">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground/60" />
          <input
            type="text"
            value={searchQuery}
            onChange={(event) => setSearchQuery(event.target.value)}
            placeholder="Search events"
            className="w-full rounded-lg border border-border/40 bg-card px-9 py-2 text-sm text-foreground placeholder:text-muted-foreground/50 focus:outline-none focus:ring-1 focus:ring-primary/30"
          />
        </div>
      </header>

      {loading && (
        <div className="rounded-xl border border-border/40 bg-card/40 p-6 text-sm text-muted-foreground">
          Loading calendar events...
        </div>
      )}

      {error && (
        <div className="rounded-xl border border-destructive/50 bg-destructive/10 p-4 text-sm text-destructive">
          <p>{error}</p>
          {calendarNotConnected && (
            <Button
              type="button"
              variant="outline"
              className="mt-3"
              onClick={handleConnectGoogleCalendar}
              disabled={connectingGoogle}
            >
              {connectingGoogle ? "Redirecting to Google..." : "Connect Google Calendar"}
            </Button>
          )}
        </div>
      )}

      {!loading && !error && (
        <section className="min-h-180 rounded-2xl border border-border/40 bg-card/40 p-5">
          <CalendarView
            events={filteredEvents}
            onCreateEvent={handleCreateEvent}
            onUpdateEvent={handleUpdateEvent}
            onDeleteEvent={handleDeleteEvent}
          />
        </section>
      )}

      <section className="rounded-2xl border border-border/40 bg-card/40 p-5">
        <div className="mb-3">
          <h2 className="text-lg font-semibold text-foreground">Calendar Sub-Agent</h2>
          <p className="text-sm text-muted-foreground">
            Use natural language to manage Google Calendar meetings from NUMA.
          </p>
        </div>

        <div className="mb-3 max-h-72 space-y-2 overflow-y-auto rounded-xl border border-border/30 bg-background/40 p-3">
          {agentMessages.map((message, index) => (
            <div
              key={`${message.role}-${index}`}
              className={
                message.role === "user"
                  ? "ml-auto w-fit max-w-[85%] rounded-lg bg-primary/15 px-3 py-2 text-sm text-foreground"
                  : "mr-auto w-fit max-w-[85%] rounded-lg bg-muted/60 px-3 py-2 text-sm text-foreground"
              }
            >
              {message.content}
            </div>
          ))}
        </div>

        {agentError && <p className="mb-2 text-sm text-destructive">{agentError}</p>}

        <div className="flex gap-2">
          <input
            value={agentInput}
            onChange={(event) => setAgentInput(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault()
                void handleSendAgentMessage()
              }
            }}
            placeholder="Try: Schedule a meeting tomorrow at 10 AM called Product Sync"
            className="flex-1 rounded-lg border border-border/40 bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground/50 focus:outline-none focus:ring-1 focus:ring-primary/30"
            disabled={agentSending}
          />
          <Button type="button" onClick={() => void handleSendAgentMessage()} disabled={agentSending}>
            {agentSending ? "Sending..." : "Send"}
          </Button>
        </div>
      </section>
    </div>
  )
}
