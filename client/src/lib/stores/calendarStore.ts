import { create } from "zustand"
import {
  CalendarEvent,
  CalendarEventPayload,
  AgentChatMessage,
  fetchCalendarEvents,
  createCalendarEvent,
  updateCalendarEvent,
  deleteCalendarEvent,
} from "@/components/calendar/api"

interface CalendarStore {
  // State
  events: CalendarEvent[]
  loading: boolean
  error: string | null
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

export const useCalendarStore = create<CalendarStore>((set, get) => ({
  events: [],
  loading: false,
  error: null,
  lastFetchedAt: null,
  agentMessages: [
    {
      role: "assistant",
      content: "I am your Calendar sub-agent. Ask me to create, move, or cancel meetings. Changes sync to both Google Calendar and your task list.",
    },
  ],

  fetchEvents: async (forceFresh = false) => {
    const { lastFetchedAt, loading } = get()
    const now = Date.now()

    // Skip if already loading
    if (loading) return

    // Skip if cache is still valid and not forcing fresh
    if (!forceFresh && lastFetchedAt && now - lastFetchedAt < CACHE_DURATION) {
      return
    }

    // Only show loading state on first fetch
    if (!lastFetchedAt) {
      set({ loading: true })
    }

    try {
      set({ error: null })
      const data = await fetchCalendarEvents(7)
      set({ events: data, lastFetchedAt: now })
    } catch (err) {
      set({ error: err instanceof Error ? err.message : "Failed to load calendar events" })
    } finally {
      set({ loading: false })
    }
  },

  createEvent: async (payload) => {
    // Optimistic update
    const tempEvent: CalendarEvent = {
      id: `temp-${Date.now()}`,
      title: payload.title,
      date: new Date(payload.date),
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
      const payload: CalendarEventPayload = {
        title: event.title,
        date: event.date.toISOString().slice(0, 10),
        startTime: event.startTime,
        endTime: event.endTime,
        description: event.description,
      }
      const updated = await updateCalendarEvent(event.id, payload)
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

  setAgentMessages: (messages) => set({ agentMessages: messages }),

  addAgentMessage: (message) =>
    set((state) => ({ agentMessages: [...state.agentMessages, message] })),

  clearError: () => set({ error: null }),
}))
