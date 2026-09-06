/**
 * Calendar transforms (NUMA-114 P4, PLAN 21.2).
 *
 * Pure API-DTO <-> view-model mappers. The wire `date` is a `YYYY-MM-DD`
 * string; the view model carries a `Date`, exactly as the old
 * `components/calendar/api.ts` mapping did.
 */
import type { CalendarEvent, CalendarEventDto, CalendarEventPayload } from "./calendar.types"
import { fromDateParam, toDateParam } from "./calendar.utils"

export function toCalendarEvent(dto: CalendarEventDto): CalendarEvent {
  return {
    id: dto.id,
    title: dto.title,
    date: fromDateParam(dto.date),
    startTime: dto.startTime,
    endTime: dto.endTime,
    description: dto.description,
    color: dto.color ?? undefined,
    calendarName: dto.calendarName ?? undefined,
    readonly: dto.readonly,
  }
}

export function toEventPayload(event: CalendarEvent): CalendarEventPayload {
  return {
    title: event.title,
    date: toDateParam(event.date),
    startTime: event.startTime,
    endTime: event.endTime,
    description: event.description,
  }
}
