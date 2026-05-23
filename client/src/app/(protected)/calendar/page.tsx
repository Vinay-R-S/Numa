"use client"

import { useCallback, useEffect, useMemo, useRef, useState } from "react"
import { CalendarDays, RefreshCw, Search, Sparkles, Square, X } from "lucide-react"

import CalendarView from "@/components/calendar/CalendarView"
import DayTimeline from "@/components/calendar/DayTimeline"
import { EventEditDialog } from "@/components/calendar/EventEditDialog"
import { AgentSuggestions } from "@/components/calendar/AgentSuggestions"
import { AgentMessageContent } from "@/components/agents/AgentMessageContent"
import { Button } from "@/components/ui/button"
import { HeaderActionButton } from "@/components/ui/header-action-button"
import { useCalendarStore } from "@/lib/stores"
import {
  AgentChatMessage,
  CalendarEvent,
  CalendarEventPayload,
  getGoogleCalendarAuthorizationUrl,
  sendAgentCommand,
  startCalendarWatch,
  subscribeToCalendarUpdates,
} from "@/components/calendar/api"

type TimelineSettings = {
  updateIntervalMs?: number
  waterEnabled?: boolean
  waterConfig?: { startHour: number; endHour: number; stepMinutes: number }
  mealTimes?: { breakfast: string; lunch: string; dinner: string }
}

function isAbortError(error: unknown): boolean {
  return error instanceof DOMException && error.name === "AbortError"
}

export default function CalendarPage() {
  // Use global store for cached data
  const {
    events,
    loading,
    error,
    calendarConnected,
    agentMessages,
    fetchEvents,
    createEvent,
    updateEvent,
    deleteEvent,
    setAgentMessages,
    addAgentMessage,
    clearError,
  } = useCalendarStore()

  const [connectingGoogle, setConnectingGoogle] = useState(false)
  const [searchQuery, setSearchQuery] = useState("")
  const [agentInput, setAgentInput] = useState("")
  const [agentSending, setAgentSending] = useState(false)
  const [agentError, setAgentError] = useState<string | null>(null)
  const [agentOpen, setAgentOpen] = useState(false)
  const [refreshingEvents, setRefreshingEvents] = useState(false)
  const [editingEvent, setEditingEvent] = useState<CalendarEvent | null>(null)
  const [timelineSettings, setTimelineSettings] = useState<TimelineSettings>({})
  const watchInitAttempted = useRef(false)
  const sseReloadTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const agentAbortRef = useRef<AbortController | null>(null)

  // Reconcile with Google on mount so external/agent edits are reflected.
  useEffect(() => {
    fetchEvents(true)
  }, [fetchEvents])

  useEffect(() => {
    try {
      const raw = localStorage.getItem("numa_timeline_settings")
      setTimelineSettings(raw ? JSON.parse(raw) : {})
    } catch {
      setTimelineSettings({})
    }
  }, [])

  useEffect(() => {
    if (!agentOpen) return

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setAgentOpen(false)
      }
    }

    window.addEventListener("keydown", onKeyDown)
    return () => window.removeEventListener("keydown", onKeyDown)
  }, [agentOpen])

  // Subscribe to SSE updates
  useEffect(() => {
    const unsubscribe = subscribeToCalendarUpdates(() => {
      // Debounce calendar reloads from SSE
      if (sseReloadTimerRef.current) {
        clearTimeout(sseReloadTimerRef.current)
      }
      sseReloadTimerRef.current = setTimeout(() => {
        fetchEvents(true) // Force fresh fetch on SSE update
      }, 500)
    })

    return () => {
      unsubscribe()
      if (sseReloadTimerRef.current) {
        clearTimeout(sseReloadTimerRef.current)
      }
    }
  }, [fetchEvents])

  // Initialize calendar watch
  useEffect(() => {
    if (watchInitAttempted.current) return

    watchInitAttempted.current = true
    startCalendarWatch().catch((err) => {
      console.error("Failed to initialize calendar watch", err)
      watchInitAttempted.current = false
    })
  }, [])

  const handleCreateEvent = useCallback(
    async (payload: CalendarEventPayload) => {
      await createEvent(payload)
    },
    [createEvent]
  )

  const handleUpdateEvent = useCallback(
    async (event: CalendarEvent) => {
      await updateEvent(event)
    },
    [updateEvent]
  )

  const handleDeleteEvent = useCallback(
    async (eventId: string) => {
      const existing = events.find((e) => e.id === eventId)
      if (existing?.readonly) return
      await deleteEvent(eventId)
    },
    [events, deleteEvent]
  )

  const handleConnectGoogleCalendar = useCallback(async () => {
    setConnectingGoogle(true)
    try {
      const authorizationUrl = await getGoogleCalendarAuthorizationUrl()
      window.location.assign(authorizationUrl)
    } catch {
      clearError()
      setConnectingGoogle(false)
    }
  }, [clearError])

  const handleRefreshEvents = useCallback(async () => {
    if (refreshingEvents) return

    setRefreshingEvents(true)
    try {
      await fetchEvents(true)
    } finally {
      setRefreshingEvents(false)
    }
  }, [fetchEvents, refreshingEvents])


  const handleSendAgentMessage = useCallback(async () => {
    const query = agentInput.trim()
    if (!query || agentSending) return

    const controller = new AbortController()
    agentAbortRef.current = controller
    const nextHistory: AgentChatMessage[] = [...agentMessages, { role: "user", content: query }]
    setAgentMessages(nextHistory)
    setAgentInput("")
    setAgentSending(true)
    setAgentError(null)

    try {
      const result = await sendAgentCommand(query, nextHistory, controller.signal)
      addAgentMessage({ role: "assistant", content: result.response })

      if (result.refreshCalendar) {
        await fetchEvents(true) // Force fresh fetch
      }
    } catch (err) {
      if (isAbortError(err)) {
        addAgentMessage({ role: "assistant", content: "Generation stopped." })
        return
      }
      const message = err instanceof Error ? err.message : "Calendar sub-agent request failed"
      setAgentError(message)
      addAgentMessage({ role: "assistant", content: `I hit an error: ${message}` })
    } finally {
      if (agentAbortRef.current === controller) {
        agentAbortRef.current = null
      }
      setAgentSending(false)
    }
  }, [agentInput, agentSending, agentMessages, setAgentMessages, addAgentMessage, fetchEvents])

  const handleStopAgentMessage = useCallback(() => {
    agentAbortRef.current?.abort()
  }, [])

  const handleSelectSuggestion = useCallback(
    (query: string) => {
      setAgentInput(query)
      setTimeout(() => {
        void handleSendAgentMessage()
      }, 100)
    },
    [handleSendAgentMessage]
  )

  const filteredEvents = useMemo(() => {
    if (!searchQuery.trim()) return events

    const q = searchQuery.toLowerCase()
    return events.filter(
      (event) =>
        event.title.toLowerCase().includes(q) ||
        event.description.toLowerCase().includes(q) ||
        (event.calendarName ?? "").toLowerCase().includes(q)
    )
  }, [events, searchQuery])

  const todayEvents = useMemo(() => {
    const now = new Date()
    return events.filter(
      (e) =>
        e.date.getFullYear() === now.getFullYear() &&
        e.date.getMonth() === now.getMonth() &&
        e.date.getDate() === now.getDate()
    )
  }, [events])

  return (
    <div className="mx-auto flex h-[calc(100dvh-3rem)] w-full flex-col gap-3 overflow-hidden px-3 py-3 sm:h-dvh sm:gap-4 sm:px-6 sm:py-4">
      <header className="flex shrink-0 flex-col gap-3 sm:flex-row sm:items-center sm:justify-between sm:gap-4">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-primary/10 ring-1 ring-primary/20 sm:h-10 sm:w-10">
            <CalendarDays className="h-4 w-4 text-primary sm:h-5 sm:w-5" />
          </div>
          <div className="min-w-0">
            <h1 className="truncate text-xl font-bold tracking-tight text-foreground sm:text-2xl">Calendar</h1>
            <p className="hidden text-sm text-muted-foreground sm:block">
              Manage Google Calendar events directly from NUMA
            </p>
          </div>
        </div>

        <div className="flex w-full items-center gap-2 sm:w-auto sm:max-w-xl sm:justify-end">
          <div className="relative flex-1 sm:w-full sm:max-w-md">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground/60" />
            <input
              type="text"
              value={searchQuery}
              onChange={(event) => setSearchQuery(event.target.value)}
              placeholder="Search events"
              className="h-9 w-full rounded-xl border border-border/40 bg-card px-9 py-2 text-sm text-foreground placeholder:text-muted-foreground/50 focus:outline-none focus:ring-1 focus:ring-primary/30 sm:h-10"
            />
          </div>

          <HeaderActionButton
            icon={RefreshCw}
            label="Refresh"
            loading={refreshingEvents || loading}
            onClick={() => { void handleRefreshEvents() }}
            disabled={refreshingEvents || loading}
            title={refreshingEvents || loading ? "Refreshing calendar" : "Refresh calendar"}
          />

          <HeaderActionButton
            icon={Sparkles}
            label="Agent"
            active={agentOpen}
            onClick={() => setAgentOpen((open) => !open)}
          />
        </div>
      </header>

      {loading && (
        <div className="shrink-0 rounded-xl border border-border/40 bg-card/40 p-3 text-sm text-muted-foreground sm:p-4">
          Loading calendar events...
        </div>
      )}

      {/* Calendar not connected - show a clean prompt, not a red error */}
      {!loading && !calendarConnected && (
        <div className="shrink-0 rounded-xl border border-amber-500/30 bg-amber-500/10 p-3 sm:p-4">
          <div className="mb-2 flex items-center gap-2">
            <CalendarDays className="h-4 w-4 text-amber-400" />
            <p className="text-sm font-medium text-amber-400">Google Calendar not connected</p>
          </div>
          <p className="mb-3 text-xs text-muted-foreground">
            Connect your Google Calendar to sync events, holidays, and birthdays with NUMA.
          </p>
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={handleConnectGoogleCalendar}
            disabled={connectingGoogle}
          >
            {connectingGoogle ? "Redirecting to Google..." : "Connect Google Calendar"}
          </Button>
        </div>
      )}

      {/* Generic errors (not connection-related) */}
      {error && (
        <div className="shrink-0 rounded-xl border border-destructive/50 bg-destructive/10 p-3 text-sm text-destructive">
          <p>{error}</p>
        </div>
      )}

      {!loading && (
        <div className="flex min-h-0 flex-1 gap-3 overflow-hidden sm:gap-4">
          <section className="min-h-0 min-w-0 flex-1 overflow-hidden rounded-xl border border-border/40 bg-card/40 p-2 sm:rounded-2xl sm:p-4">
            <CalendarView
              events={filteredEvents}
              onCreateEvent={handleCreateEvent}
              onUpdateEvent={handleUpdateEvent}
              onDeleteEvent={handleDeleteEvent}
              onEditEvent={setEditingEvent}
            />
          </section>

          <aside className="hidden h-full w-[320px] shrink-0 lg:block">
            <DayTimeline
              calendarEvents={todayEvents}
              updateIntervalMs={timelineSettings.updateIntervalMs}
              waterConfig={timelineSettings.waterEnabled === false ? { startHour: 0, endHour: 0, stepMinutes: 60 } : timelineSettings.waterConfig}
              mealTimes={timelineSettings.mealTimes}
            />
          </aside>
        </div>
      )}

      {editingEvent && (
        <EventEditDialog
          event={editingEvent}
          onClose={() => setEditingEvent(null)}
          onSave={handleUpdateEvent}
          onDelete={handleDeleteEvent}
        />
      )}

      {agentOpen && (
        <section className="fixed inset-x-3 bottom-3 top-auto z-40 flex max-h-[70vh] flex-col rounded-2xl border border-border/40 bg-card/95 p-3 shadow-2xl backdrop-blur-md sm:inset-auto sm:right-6 sm:top-24 sm:h-[min(70vh,640px)] sm:w-[min(420px,calc(100vw-3rem))] sm:p-4">
          <div className="mb-3 flex items-center justify-between">
            <div className="min-w-0">
              <h2 className="truncate text-base font-semibold text-foreground">Calendar Sub-Agent</h2>
              <p className="truncate text-xs text-muted-foreground">Plan and manage meetings with natural language.</p>
            </div>
            <Button
              type="button"
              variant="ghost"
              size="icon"
              className="h-8 w-8 shrink-0"
              onClick={() => setAgentOpen(false)}
            >
              <X className="h-4 w-4" />
            </Button>
          </div>

          <div className="mb-3 min-h-0 flex-1 space-y-2 overflow-y-auto rounded-xl border border-border/30 bg-background/40 p-2 sm:p-3">
            {agentMessages.map((message, index) => (
              <div
                key={`${message.role}-${index}`}
                className={
                  message.role === "user"
                    ? "ml-auto min-w-0 max-w-[90%] overflow-hidden rounded-lg bg-primary/15 px-3 py-2 text-sm text-foreground"
                    : "mr-auto min-w-0 max-w-[90%] overflow-hidden rounded-lg bg-muted/60 px-3 py-2 text-sm text-foreground"
                }
              >
                <AgentMessageContent content={message.content} />
              </div>
            ))}
            {agentSending && (
              <div className="mr-auto w-fit max-w-[90%] rounded-lg bg-muted/60 px-3 py-2 text-sm text-muted-foreground">
                Thinking and generating output...
              </div>
            )}
          </div>

          {agentMessages.length <= 2 && (
            <AgentSuggestions events={events} onSelectSuggestion={handleSelectSuggestion} />
          )}

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
              placeholder="Try: Schedule product sync tomorrow at 10 AM"
              className="flex-1 rounded-lg border border-border/40 bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground/50 focus:outline-none focus:ring-1 focus:ring-primary/30"
              disabled={agentSending}
            />
            <Button
              type="button"
              size="sm"
              variant={agentSending ? "destructive" : "default"}
              className="shrink-0 sm:size-default"
              onClick={() => agentSending ? handleStopAgentMessage() : void handleSendAgentMessage()}
              disabled={!agentInput.trim() && !agentSending}
            >
              {agentSending ? <Square className="h-4 w-4" /> : "Send"}
            </Button>
          </div>
        </section>
      )}
    </div>
  )
}
