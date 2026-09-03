/**
 * Calendar domain types (NUMA-114 P4, PLAN 5.3 / 21.2).
 *
 * `CalendarEventDto` is the wire shape returned by `server/src/calendar`
 * (`date` is a `YYYY-MM-DD` string); `CalendarEvent` is the view model used
 * across the feature, with `date` parsed to a `Date` by `calendar.transforms`.
 */

export interface CalendarEventDto {
  id: string
  title: string
  date: string
  startTime: string
  endTime: string
  description: string
  color?: string | null
  calendarName?: string | null
  readonly?: boolean
}

export interface CalendarEvent {
  id: string
  title: string
  date: Date
  startTime: string
  endTime: string
  description: string
  color?: string
  calendarName?: string
  readonly?: boolean
}

export interface CalendarEventPayload {
  title: string
  date: string
  startTime: string
  endTime: string
  description: string
}

export interface EventsResponse {
  events: CalendarEventDto[]
}

export interface DeleteResponse {
  success: boolean
}

export interface WatchStartResponse {
  success: boolean
  channel_id?: string | null
  resource_id?: string | null
  expiration?: string | null
}

export interface StreamTokenResponse {
  token: string
  expires_in: number
}

export interface OAuthStartResponse {
  authorization_url: string
}

export interface TokenHealthResult {
  valid: boolean
  connected: boolean
  reason?: string | null
  reconnect_url?: string | null
}

export interface AgentChatMessage {
  role: "user" | "assistant"
  content: string
}

export interface AgentChatResponse {
  response: string
  success?: boolean
  refreshCalendar?: boolean
}

export type ViewMode = "month" | "week" | "day"

export interface AnchorRect {
  top: number
  right: number
  bottom: number
  left: number
  width: number
  height: number
}

export interface Viewport {
  width: number
  height: number
}

export interface Point {
  x: number
  y: number
}

export interface TimelineSettings {
  updateIntervalMs?: number
  waterEnabled?: boolean
  waterConfig?: { startHour: number; endHour: number; stepMinutes: number }
  mealTimes?: { breakfast: string; lunch: string; dinner: string }
}

export type TimelineItemType = "calendar" | "task" | "meal" | "water"
export type TimelineItemState = "upcoming" | "active" | "completed"

export interface TimelineItem {
  id: string
  type: TimelineItemType
  title: string
  time: string
  endTime?: string
  description?: string
  state: TimelineItemState
}
