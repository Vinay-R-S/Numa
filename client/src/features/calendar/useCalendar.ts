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
import { SSE_RELOAD_DEBOUNCE_MS } from "./calendar.constants"
import { readTimelineSettings } from "./calendar.settings"
import { eventsForDay, filterEventsByQuery } from "./calendar.utils"
import type { CalendarEvent, CalendarEventPayload, TimelineSettings } from "./calendar.types"

export function useCalendar() {
  // Selector per slice, not the whole store: subscribing to the store object
  // re-rendered the month grid on every agent message (NUMA-142 P6, PLAN 9).
  const events = useCalendarStore((state) => state.events)
  const loading = useCalendarStore((state) => state.loading)
  const error = useCalendarStore((state) => state.error)
  const calendarConnected = useCalendarStore((state) => state.calendarConnected)
  const fetchEvents = useCalendarStore((state) => state.fetchEvents)
  const createEvent = useCalendarStore((state) => state.createEvent)
  const updateEvent = useCalendarStore((state) => state.updateEvent)
  const deleteEvent = useCalendarStore((state) => state.deleteEvent)

  const [connectingGoogle, setConnectingGoogle] = useState(false)
  const [connectError, setConnectError] = useState<string | null>(null)
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
    setConnectError(null)
    try {
      const authorizationUrl = await getGoogleCalendarAuthorizationUrl()
      globalThis.location.assign(authorizationUrl)
    } catch (err) {
      // This cleared the store's unrelated event-loading error and showed the
      // user nothing, so a failed connect looked like a button that did not
      // work (NUMA-142 P6, PLAN 7).
      setConnectError(
        err instanceof Error ? err.message : "Could not start Google Calendar authorization"
      )
      setConnectingGoogle(false)
    }
  }, [])

  const handleRefreshEvents = useCallback(async () => {
    if (refreshingEvents) return

    setRefreshingEvents(true)
    try {
      await fetchEvents(true)
      // A successful load clears the connect failure. It was only ever reset
      // inside the connect handler, so one failed attempt masked the store's
      // own error for the rest of the session with no way to dismiss it
      // (NUMA-142 P6 review).
      setConnectError(null)
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
    // The store's own error, or the connect failure this hook owns.
    error: connectError ?? error,
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
