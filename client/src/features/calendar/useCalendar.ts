/**
 * Calendar page data hook (NUMA-114 P4, PLAN 21.2).
 *
 * Owns everything the calendar route used to do inline: the store binding,
 * search box, refresh/connect actions, the Google watch bootstrap, the SSE
 * subscription (debounced) and the timeline settings read from localStorage.
 * The page consumes only this hook and composes presentational components.
 */
import { useCallback, useEffect, useMemo, useRef, useState } from "react"

import { useCalendarStore } from "@/lib/stores"
import { getGoogleCalendarAuthorizationUrl, startCalendarWatch, subscribeToCalendarUpdates } from "./calendar.api"
import { SSE_RELOAD_DEBOUNCE_MS, TIMELINE_SETTINGS_KEY } from "./calendar.constants"
import { eventsForDay, filterEventsByQuery } from "./calendar.utils"
import type { CalendarEvent, CalendarEventPayload, TimelineSettings } from "./calendar.types"

function readTimelineSettings(): TimelineSettings {
  try {
    const raw = localStorage.getItem(TIMELINE_SETTINGS_KEY)
    return raw ? (JSON.parse(raw) as TimelineSettings) : {}
  } catch {
    return {}
  }
}

export function useCalendar() {
  const {
    events,
    loading,
    error,
    calendarConnected,
    fetchEvents,
    createEvent,
    updateEvent,
    deleteEvent,
    clearError,
  } = useCalendarStore()

  const [connectingGoogle, setConnectingGoogle] = useState(false)
  const [searchQuery, setSearchQuery] = useState("")
  const [refreshingEvents, setRefreshingEvents] = useState(false)
  const [editingEvent, setEditingEvent] = useState<CalendarEvent | null>(null)
  const [timelineSettings, setTimelineSettings] = useState<TimelineSettings>({})
  const watchInitAttempted = useRef(false)
  const sseReloadTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  // Reconcile with Google on mount so external/agent edits are reflected.
  useEffect(() => {
    fetchEvents(true)
  }, [fetchEvents])

  useEffect(() => {
    setTimelineSettings(readTimelineSettings())
  }, [])

  useEffect(() => {
    const unsubscribe = subscribeToCalendarUpdates(() => {
      if (sseReloadTimerRef.current) clearTimeout(sseReloadTimerRef.current)
      sseReloadTimerRef.current = setTimeout(() => fetchEvents(true), SSE_RELOAD_DEBOUNCE_MS)
    })

    return () => {
      unsubscribe()
      if (sseReloadTimerRef.current) clearTimeout(sseReloadTimerRef.current)
    }
  }, [fetchEvents])

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
      const existing = events.find((event) => event.id === eventId)
      if (existing?.readonly) return
      await deleteEvent(eventId)
    },
    [events, deleteEvent]
  )

  const handleConnectGoogleCalendar = useCallback(async () => {
    setConnectingGoogle(true)
    try {
      const authorizationUrl = await getGoogleCalendarAuthorizationUrl()
      globalThis.location.assign(authorizationUrl)
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

  const filteredEvents = useMemo(() => filterEventsByQuery(events, searchQuery), [events, searchQuery])
  const todayEvents = useMemo(() => eventsForDay(events, new Date()), [events])

  return {
    events,
    filteredEvents,
    todayEvents,
    loading,
    error,
    calendarConnected,
    connectingGoogle,
    refreshingEvents,
    searchQuery,
    editingEvent,
    timelineSettings,
    setSearchQuery,
    setEditingEvent,
    handleCreateEvent,
    handleUpdateEvent,
    handleDeleteEvent,
    handleConnectGoogleCalendar,
    handleRefreshEvents,
  }
}

export type UseCalendarReturn = ReturnType<typeof useCalendar>
