/**
 * Calendar feature module public surface (NUMA-114 P4, PLAN 5.3 / 21.2).
 *
 * Cross-page calendar state lives in the `useCalendarStore` zustand store
 * (`lib/stores/calendarStore.ts`) as the single source of truth (PLAN 9); it
 * consumes this module's api/types.
 */
export * from "./calendar.types"
export * from "./calendar.api"
export * from "./calendar.schema"
export * from "./calendar.transforms"
export * from "./calendar.utils"
export * from "./calendar.constants"

export { useCalendar } from "./useCalendar"
export type { UseCalendarReturn } from "./useCalendar"
export { useCalendarAgent } from "./useCalendarAgent"
export type { UseCalendarAgentReturn } from "./useCalendarAgent"
export { useCalendarView } from "./useCalendarView"
export type { UseCalendarViewReturn } from "./useCalendarView"
export { useDayTimeline } from "./useDayTimeline"
export type { UseDayTimelineReturn } from "./useDayTimeline"

export { CalendarView } from "./components/CalendarView"
export { CalendarToolbar } from "./components/CalendarToolbar"
export { MonthGrid } from "./components/MonthGrid"
export { WeekGrid } from "./components/WeekGrid"
export { DayGrid } from "./components/DayGrid"
export { DayEventBlock } from "./components/DayEventBlock"
export { EventChip } from "./components/EventChip"
export { EventDetailPopup } from "./components/EventDetailPopup"
export { CreateEventPopup } from "./components/CreateEventPopup"
export { EventEditDialog } from "./components/EventEditDialog"
export { AgentSuggestions } from "./components/AgentSuggestions"
export { CalendarAgentPanel } from "./components/CalendarAgentPanel"
export { CalendarPageHeader } from "./components/CalendarPageHeader"
export { CalendarConnectPrompt } from "./components/CalendarConnectPrompt"
export { DayTimeline } from "./components/DayTimeline"
export { TimelineItemRow, TimelineNowRow } from "./components/TimelineRow"
