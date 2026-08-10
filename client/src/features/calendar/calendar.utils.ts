/**
 * Calendar pure helpers (NUMA-114 P4, PLAN 21.2).
 *
 * Grid maths, time formatting and popup placement extracted from the old
 * `CalendarView.tsx` / `DayTimeline.tsx` / `calendar/page.tsx`. All pure, so
 * the presentational components only render.
 */
import {
  DAY_START_HOUR,
  DESKTOP_BREAKPOINT,
  SIDEBAR_RAIL_WIDTH,
} from "./calendar.constants"
import type {
  AnchorRect,
  CalendarEvent,
  Point,
  TimelineItemState,
  Viewport,
} from "./calendar.types"

export function isSameDay(a: Date, b: Date): boolean {
  return (
    a.getFullYear() === b.getFullYear() &&
    a.getMonth() === b.getMonth() &&
    a.getDate() === b.getDate()
  )
}

/** Month grid padded with nulls so it always starts on Sunday and fills whole weeks. */
export function getMonthGrid(year: number, month: number): (Date | null)[] {
  const first = new Date(year, month, 1)
  const last = new Date(year, month + 1, 0)
  const days: (Date | null)[] = []

  for (let i = 0; i < first.getDay(); i += 1) days.push(null)
  for (let day = 1; day <= last.getDate(); day += 1) days.push(new Date(year, month, day))
  while (days.length % 7 !== 0) days.push(null)

  return days
}

export function getWeekDates(date: Date): Date[] {
  const start = new Date(date)
  start.setDate(start.getDate() - start.getDay())
  return Array.from({ length: 7 }, (_, index) => {
    const day = new Date(start)
    day.setDate(day.getDate() + index)
    return day
  })
}

export function formatHour(hour: number): string {
  if (hour > 12) return `${hour - 12}PM`
  if (hour === 12) return "12PM"
  return `${hour}AM`
}

export function timeToMinutes(value: string): number {
  const [hours, minutes] = value.split(":").map(Number)
  return hours * 60 + (minutes || 0)
}

export function minutesToTime(value: number): string {
  const hours = Math.floor(value / 60)
  const minutes = value % 60
  return `${String(hours).padStart(2, "0")}:${String(minutes).padStart(2, "0")}`
}

export function formatTime12(value: string): string {
  const [hours, minutes] = value.split(":").map(Number)
  const period = hours >= 12 ? "PM" : "AM"
  const display = hours % 12 || 12
  return `${display}:${String(minutes).padStart(2, "0")} ${period}`
}

export function nowHHMM(): string {
  const now = new Date()
  return `${String(now.getHours()).padStart(2, "0")}:${String(now.getMinutes()).padStart(2, "0")}`
}

/** `YYYY-MM-DD` request/date-input value. */
export function toDateParam(date: Date): string {
  return date.toISOString().slice(0, 10)
}

export function eventsForDay(events: CalendarEvent[], date: Date): CalendarEvent[] {
  return events.filter((event) => isSameDay(event.date, date))
}

/**
 * Index events by local day key so a grid can look each cell up instead of
 * re-filtering the whole month per cell (the week grid renders 105 of them).
 */
export function groupEventsByDay(events: CalendarEvent[]): Map<string, CalendarEvent[]> {
  const grouped = new Map<string, CalendarEvent[]>()

  events.forEach((event) => {
    const key = dayKey(event.date)
    const bucket = grouped.get(key)
    if (bucket) {
      bucket.push(event)
      return
    }
    grouped.set(key, [event])
  })

  return grouped
}

/** Local-calendar day key. Not `toDateParam`, which converts to UTC. */
export function dayKey(date: Date): string {
  return `${date.getFullYear()}-${date.getMonth()}-${date.getDate()}`
}

export function filterEventsByQuery(events: CalendarEvent[], query: string): CalendarEvent[] {
  const term = query.trim().toLowerCase()
  if (!term) return events

  return events.filter(
    (event) =>
      event.title.toLowerCase().includes(term) ||
      event.description.toLowerCase().includes(term) ||
      (event.calendarName ?? "").toLowerCase().includes(term)
  )
}

export function isAbortError(error: unknown): boolean {
  return error instanceof DOMException && error.name === "AbortError"
}

export function timelineItemState(
  time: string,
  endTime: string | undefined,
  nowStr: string
): TimelineItemState {
  const nowMinutes = timeToMinutes(nowStr)
  const startMinutes = timeToMinutes(time)
  const endMinutes = endTime ? timeToMinutes(endTime) : startMinutes + 15

  if (nowMinutes >= endMinutes) return "completed"
  if (nowMinutes >= startMinutes) return "active"
  return "upcoming"
}

/** Vertical placement of an event block inside the day grid. */
export function eventBlockGeometry(startTime: string, endTime: string, slotHeight: number) {
  const startMinutes = timeToMinutes(startTime)
  const endMinutes = timeToMinutes(endTime)
  const top = ((startMinutes - DAY_START_HOUR * 60) / 60) * slotHeight
  const height = ((endMinutes - startMinutes) / 60) * slotHeight
  return { startMinutes, endMinutes, top, height }
}

function leftBoundFor(viewport: Viewport, margin: number): number {
  return viewport.width >= DESKTOP_BREAKPOINT ? SIDEBAR_RAIL_WIDTH + margin : margin
}

/**
 * Place the hover detail popup beside its anchor: prefer right, then left,
 * otherwise centre it; always clamped inside the viewport and clear of the
 * sidebar rail.
 */
export function detailPopupPosition(
  anchorRect: AnchorRect,
  popupSize: { width: number; height: number },
  viewport: Viewport
): Point {
  const margin = 12
  const gap = 10
  const leftBound = leftBoundFor(viewport, margin)

  const spaceRight = viewport.width - anchorRect.right
  const spaceLeft = anchorRect.left - leftBound
  const spaceBottom = viewport.height - anchorRect.bottom
  const spaceTop = anchorRect.top

  let left: number
  if (spaceRight >= popupSize.width + gap) {
    left = anchorRect.right + gap
  } else if (spaceLeft >= popupSize.width + gap) {
    left = anchorRect.left - popupSize.width - gap
  } else {
    left = leftBound + (viewport.width - leftBound - popupSize.width) / 2
  }

  let top = anchorRect.top + (anchorRect.height - popupSize.height) / 2

  if (top < margin && spaceBottom >= popupSize.height + gap) {
    top = anchorRect.bottom + gap
  } else if (
    top + popupSize.height > viewport.height - margin &&
    spaceTop >= popupSize.height + gap
  ) {
    top = anchorRect.top - popupSize.height - gap
  }

  return {
    x: Math.max(leftBound, Math.min(left, viewport.width - popupSize.width - margin)),
    y: Math.max(margin, Math.min(top, viewport.height - popupSize.height - margin)),
  }
}

/** Place the create popup under the click point, flipping above when it would overflow. */
export function createPopupPosition(
  origin: Point,
  popupSize: { width: number; height: number },
  viewport: Viewport
): Point {
  const margin = 12
  const gap = 8
  const leftBound = leftBoundFor(viewport, margin)

  const left = origin.x - popupSize.width / 2
  let top = origin.y + gap

  if (top + popupSize.height > viewport.height - margin) {
    top = origin.y - popupSize.height - gap
  }

  return {
    x: Math.max(leftBound, Math.min(left, viewport.width - popupSize.width - margin)),
    y: Math.max(margin, Math.min(top, viewport.height - popupSize.height - margin)),
  }
}
