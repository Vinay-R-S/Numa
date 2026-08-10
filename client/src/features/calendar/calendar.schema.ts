/**
 * Calendar validation schemas (NUMA-114 P4, PLAN 22.2 / 22.3).
 *
 * Mirrors the Pydantic DTOs in `server/src/calendar/schemas.py` and
 * `server/src/calendar_agent/schemas.py`. Response schemas run through the
 * shared `http` `schema` option so contract drift fails loudly; the input
 * schemas mirror the server-side bounds for the create/edit forms.
 *
 * Optional/nullish fields follow the server: `color`, `calendarName` are
 * `Optional[str]`, `readonly` has a default, and the agent envelope keeps
 * `success`/`refreshCalendar` tolerant so a body-less agent reply still parses.
 */
import { z } from "@/lib/validation"
import type {
  AgentChatResponse,
  CalendarEventDto,
  DeleteResponse,
  EventsResponse,
  OAuthStartResponse,
  TokenHealthResult,
  WatchStartResponse,
} from "./calendar.types"

const DATE_PATTERN = /^\d{4}-\d{2}-\d{2}$/
const TIME_PATTERN = /^\d{2}:\d{2}$/

export const calendarEventDtoSchema: z.ZodType<CalendarEventDto> = z.object({
  id: z.string(),
  title: z.string(),
  date: z.string(),
  startTime: z.string(),
  endTime: z.string(),
  description: z.string(),
  color: z.string().nullish(),
  calendarName: z.string().nullish(),
  readonly: z.boolean().optional(),
})

export const eventsResponseSchema: z.ZodType<EventsResponse> = z.object({
  events: z.array(calendarEventDtoSchema),
})

export const deleteResponseSchema: z.ZodType<DeleteResponse> = z.object({
  success: z.boolean(),
})

export const watchStartResponseSchema: z.ZodType<WatchStartResponse> = z.object({
  success: z.boolean(),
  channel_id: z.string().nullish(),
  resource_id: z.string().nullish(),
  expiration: z.string().nullish(),
})

export const oauthStartResponseSchema: z.ZodType<OAuthStartResponse> = z.object({
  authorization_url: z.string(),
})

export const tokenHealthSchema: z.ZodType<TokenHealthResult> = z.object({
  valid: z.boolean(),
  connected: z.boolean(),
  reason: z.string().nullish(),
  reconnect_url: z.string().nullish(),
})

export const agentChatResponseSchema: z.ZodType<AgentChatResponse> = z.object({
  response: z.string(),
  success: z.boolean().optional(),
  refreshCalendar: z.boolean().optional(),
})

/** Input schema for the create/edit forms; mirrors `CalendarEventUpsert`. */
export const calendarEventUpsertSchema = z.object({
  title: z.string().trim().min(1),
  date: z.string().regex(DATE_PATTERN, "Expected YYYY-MM-DD"),
  startTime: z.string().regex(TIME_PATTERN, "Expected HH:MM"),
  endTime: z.string().regex(TIME_PATTERN, "Expected HH:MM"),
  description: z.string().default(""),
})

export type CalendarEventUpsertInput = z.infer<typeof calendarEventUpsertSchema>
