import { create } from "zustand"
import { ApiError } from "@/lib/http"
import type {
  AgentChatMessage,
  CalendarEvent,
  CalendarEventPayload,
} from "@/features/calendar/calendar.types"
import {
  createCalendarEvent,
  deleteCalendarEvent,
  fetchCalendarEvents,
  updateCalendarEvent,
} from "@/features/calendar/calendar.api"
import { toEventPayload } from "@/features/calendar/calendar.transforms"
import { fromDateParam } from "@/features/calendar/calendar.utils"
import { loadSessionMessages, saveSessionMessages } from "@/lib/useSessionMessages"

const CALENDAR_AGENT_SESSION_KEY = "numa:session:calendar-agent-chat"
const DEFAULT_CALENDAR_AGENT_MESSAGES: AgentChatMessage[] = [
  {
    role: "assistant",
    content: "I am your Calendar sub-agent. Ask me to create, move, or cancel meetings. Changes sync to both Google Calendar and your task list.",
  },
]

interface CalendarStore {
  // State
  events: CalendarEvent[]
  loading: boolean
  error: string | null
  calendarConnected: boolean   // false = token missing/expired, show reconnect prompt
  lastFetchedAt: number | null
  agentMessages: AgentChatMessage[]

  // Actions
  fetchEvents: (forceFresh?: boolean) => Promise<void>
  createEvent: (payload: CalendarEventPayload) => Promise<CalendarEvent>
  updateEvent: (event: CalendarEvent) => Promise<CalendarEvent>
  deleteEvent: (eventId: string) => Promise<void>
  setEvents: (events: CalendarEvent[]) => void
  setAgentMessages: (messages: AgentChatMessage[]) => void
  addAgentMessage: (message: AgentChatMessage) => void
  clearError: () => void
}

// Cache duration: 5 minutes
const CACHE_DURATION = 5 * 60 * 1000

// In-flight tracking lives here, not in the `loading` UI flag. `loading` is only
// set on the very first fetch (so a refresh does not blank the grid), which made
// the `if (loading) return` dedup guard unreachable from the second fetch on:
// two overlapping fetches both ran and the slower one overwrote the fresher
// result (NUMA-142 P6, PLAN 7).
let eventsFetchInFlight = false

export const useCalendarStore = create<CalendarStore>((set, get) => ({
  events: [],
  loading: false,
  error: null,
  calendarConnected: true,   // optimistically true; set to false on 401
  lastFetchedAt: null,
  agentMessages: loadSessionMessages(CALENDAR_AGENT_SESSION_KEY, DEFAULT_CALENDAR_AGENT_MESSAGES),

  fetchEvents: async (forceFresh = false) => {
    const { lastFetchedAt } = get()
    const now = Date.now()

    if (eventsFetchInFlight) return

    if (!forceFresh && lastFetchedAt && now - lastFetchedAt < CACHE_DURATION) {
      return
    }

    if (!lastFetchedAt) {
      set({ loading: true })
    }

    eventsFetchInFlight = true
    try {
      set({ error: null })
      const data = await fetchCalendarEvents(forceFresh ? { refresh: true } : undefined)
      set({ events: data, lastFetchedAt: now, calendarConnected: true })
    } catch (err) {
      // A 401 from /calendar/events means the Google token is missing or expired:
      // not an error, just not connected. Let the UI show the reconnect prompt.
      // `isAuthFailure` excludes the other 401 on this route - a dead Numa
      // session - which lib/http has already signed the user out for (NUMA-126).
      if (err instanceof ApiError && err.status === 401 && !err.isAuthFailure) {
        set({ calendarConnected: false, events: [] })
      } else {
        set({ error: err instanceof Error ? err.message : "Failed to load calendar events" })
      }
    } finally {
      eventsFetchInFlight = false
      set({ loading: false })
    }
  },

  createEvent: async (payload) => {
    // Optimistic update
    const tempEvent: CalendarEvent = {
      id: `temp-${Date.now()}`,
      title: payload.title,
      // `fromDateParam`, not `new Date`: the wire format is `YYYY-MM-DD`, which
      // JS parses as UTC midnight, so west of UTC the optimistic event rendered
      // in the previous day's cell and jumped when the server reply replaced it
      // (NUMA-142 P6 review).
      date: fromDateParam(payload.date),
      startTime: payload.startTime,
      endTime: payload.endTime,
      description: payload.description,
    }
    set((state) => ({ events: [...state.events, tempEvent] }))

    try {
      const created = await createCalendarEvent(payload)
      // Replace temp with real event
      set((state) => ({
        events: state.events.map((e) => (e.id === tempEvent.id ? created : e)),
      }))
      return created
    } catch (err) {
      // Revert on error
      set((state) => ({
        events: state.events.filter((e) => e.id !== tempEvent.id),
      }))
      throw err
    }
  },

  updateEvent: async (event) => {
    const { events } = get()
    const originalEvent = events.find((e) => e.id === event.id)

    // Optimistic update
    set((state) => ({
      events: state.events.map((e) => (e.id === event.id ? event : e)),
    }))

    try {
      const updated = await updateCalendarEvent(event.id, toEventPayload(event))
      set((state) => ({
        events: state.events.map((e) => (e.id === updated.id ? updated : e)),
      }))
      return updated
    } catch (err) {
      // Revert on error
      if (originalEvent) {
        set((state) => ({
          events: state.events.map((e) => (e.id === event.id ? originalEvent : e)),
        }))
      }
      throw err
    }
  },

  deleteEvent: async (eventId) => {
    const { events } = get()
    const deletedEvent = events.find((e) => e.id === eventId)

    // Optimistic update
    set((state) => ({
      events: state.events.filter((e) => e.id !== eventId),
    }))

    try {
      await deleteCalendarEvent(eventId)
    } catch (err) {
      // Revert on error
      if (deletedEvent) {
        set((state) => ({ events: [...state.events, deletedEvent] }))
      }
      throw err
    }
  },

  setEvents: (events) => set({ events }),

  setAgentMessages: (messages) => {
    saveSessionMessages(CALENDAR_AGENT_SESSION_KEY, messages)
    set({ agentMessages: messages })
  },

  addAgentMessage: (message) =>
    set((state) => {
      const agentMessages = [...state.agentMessages, message]
      saveSessionMessages(CALENDAR_AGENT_SESSION_KEY, agentMessages)
      return { agentMessages }
    }),

  clearError: () => set({ error: null }),
}))
