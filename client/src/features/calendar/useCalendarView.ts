/**
 * Calendar grid hook (NUMA-114 P4, PLAN 21.2).
 *
 * Owns the month/week/day view state that used to live inside the 872-line
 * `CalendarView.tsx`: current view + date, hover/create popups, the live clock
 * and the mobile breakpoint, plus the drag/resize/delete guards. The grid
 * components stay presentational.
 */
import { useCallback, useEffect, useMemo, useRef, useState } from "react"
import type { MouseEvent as ReactMouseEvent } from "react"

import {
  MOBILE_BREAKPOINT,
  MONTHS,
  NOW_LINE_END_MINUTES,
  NOW_LINE_START_MINUTES,
  NOW_TICK_MS,
  POPUP_CLOSE_DELAY_MS,
  SLOT_HEIGHT,
} from "./calendar.constants"
import { getWeekDates, minutesToTime, timeToMinutes } from "./calendar.utils"
import type { AnchorRect, CalendarEvent, CalendarEventPayload, Point, ViewMode } from "./calendar.types"

interface UseCalendarViewOptions {
  events: CalendarEvent[]
  onCreateEvent?: (event: CalendarEventPayload) => Promise<void>
  onUpdateEvent?: (event: CalendarEvent) => Promise<void>
  onDeleteEvent?: (eventId: string) => Promise<void>
}

function isMobileViewport(): boolean {
  if (typeof window === "undefined") return false
  return globalThis.innerWidth < MOBILE_BREAKPOINT
}

function headerLabelFor(view: ViewMode, currentDate: Date): string {
  if (view === "month") return `${MONTHS[currentDate.getMonth()]} ${currentDate.getFullYear()}`

  if (view === "week") {
    const week = getWeekDates(currentDate)
    return `${MONTHS[week[0].getMonth()]} ${week[0].getDate()} - ${week[6].getDate()}, ${week[6].getFullYear()}`
  }

  return `${MONTHS[currentDate.getMonth()]} ${currentDate.getDate()}, ${currentDate.getFullYear()}`
}

export function useCalendarView({
  events,
  onCreateEvent,
  onUpdateEvent,
  onDeleteEvent,
}: UseCalendarViewOptions) {
  const [view, setView] = useState<ViewMode>(() => (isMobileViewport() ? "day" : "month"))
  const [currentDate, setCurrentDate] = useState(() => new Date())
  const [detailPopup, setDetailPopup] = useState<{ event: CalendarEvent; anchorRect: AnchorRect } | null>(null)
  const [createPopup, setCreatePopup] = useState<{ date: Date; hour: number; pos: Point } | null>(null)
  const [now, setNow] = useState(() => new Date())
  const [isMobile, setIsMobile] = useState(isMobileViewport)
  const closeTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    const id = globalThis.setInterval(() => setNow(new Date()), NOW_TICK_MS)
    return () => globalThis.clearInterval(id)
  }, [])

  useEffect(() => {
    const check = () => {
      const mobile = isMobileViewport()
      setIsMobile(mobile)
      if (mobile) setView((current) => (current === "month" ? "day" : current))
    }

    globalThis.addEventListener("resize", check)
    return () => globalThis.removeEventListener("resize", check)
  }, [])

  const closePopups = useCallback(() => {
    setDetailPopup(null)
    setCreatePopup(null)
  }, [])

  const cancelScheduledClose = useCallback(() => {
    if (!closeTimerRef.current) return
    globalThis.clearTimeout(closeTimerRef.current)
    closeTimerRef.current = null
  }, [])

  const schedulePopupClose = useCallback(() => {
    cancelScheduledClose()
    closeTimerRef.current = globalThis.setTimeout(() => setDetailPopup(null), POPUP_CLOSE_DELAY_MS)
  }, [cancelScheduledClose])

  const navigate = useCallback(
    (direction: number) => {
      setCurrentDate((current) => {
        const date = new Date(current)
        if (view === "month") date.setMonth(date.getMonth() + direction)
        else if (view === "week") date.setDate(date.getDate() + direction * 7)
        else date.setDate(date.getDate() + direction)
        return date
      })
      closePopups()
    },
    [view, closePopups]
  )

  const goToToday = useCallback(() => {
    setCurrentDate(new Date())
    closePopups()
  }, [closePopups])

  const changeView = useCallback(
    (mode: ViewMode) => {
      setView(mode)
      closePopups()
    },
    [closePopups]
  )

  const openDay = useCallback((date: Date) => {
    setCurrentDate(date)
    setView("day")
  }, [])

  const handleSlotClick = useCallback(
    (date: Date, hour: number, mouseEvent: ReactMouseEvent) => {
      closePopups()
      setCreatePopup({ date, hour, pos: { x: mouseEvent.clientX, y: mouseEvent.clientY } })
    },
    [closePopups]
  )

  const handleEventHover = useCallback(
    (event: CalendarEvent, mouseEvent: ReactMouseEvent<HTMLElement>) => {
      cancelScheduledClose()
      setCreatePopup(null)
      const rect = mouseEvent.currentTarget.getBoundingClientRect()
      setDetailPopup({
        event,
        anchorRect: {
          top: rect.top,
          right: rect.right,
          bottom: rect.bottom,
          left: rect.left,
          width: rect.width,
          height: rect.height,
        },
      })
    },
    [cancelScheduledClose]
  )

  const handleCreate = useCallback(
    async (payload: CalendarEventPayload) => {
      if (!onCreateEvent) return
      await onCreateEvent(payload)
    },
    [onCreateEvent]
  )

  const handleDelete = useCallback(
    async (eventId: string) => {
      const existing = events.find((event) => event.id === eventId)
      if (existing?.readonly) return
      if (!onDeleteEvent) return
      await onDeleteEvent(eventId)
    },
    [events, onDeleteEvent]
  )

  const handleDragEnd = useCallback(
    async (id: string, newStartMin: number) => {
      if (!onUpdateEvent) return

      const existing = events.find((event) => event.id === id)
      if (!existing || existing.readonly) return

      const duration = timeToMinutes(existing.endTime) - timeToMinutes(existing.startTime)
      await onUpdateEvent({
        ...existing,
        startTime: minutesToTime(newStartMin),
        endTime: minutesToTime(newStartMin + duration),
      })
    },
    [events, onUpdateEvent]
  )

  const handleResizeEnd = useCallback(
    async (id: string, newEndMin: number) => {
      if (!onUpdateEvent) return

      const existing = events.find((event) => event.id === id)
      if (!existing || existing.readonly) return

      await onUpdateEvent({ ...existing, endTime: minutesToTime(newEndMin) })
    },
    [events, onUpdateEvent]
  )

  const headerLabel = useMemo(() => headerLabelFor(view, currentDate), [view, currentDate])

  const nowMinutes = now.getHours() * 60 + now.getMinutes()
  const showNowLine = nowMinutes >= NOW_LINE_START_MINUTES && nowMinutes <= NOW_LINE_END_MINUTES
  const nowTop = ((nowMinutes - NOW_LINE_START_MINUTES) / 60) * SLOT_HEIGHT

  return {
    view,
    currentDate,
    today: now,
    isMobile,
    detailPopup,
    createPopup,
    headerLabel,
    showNowLine,
    nowTop,
    navigate,
    goToToday,
    changeView,
    openDay,
    closePopups,
    cancelScheduledClose,
    schedulePopupClose,
    handleSlotClick,
    handleEventHover,
    handleCreate,
    handleDelete,
    handleDragEnd,
    handleResizeEnd,
  }
}

export type UseCalendarViewReturn = ReturnType<typeof useCalendarView>
