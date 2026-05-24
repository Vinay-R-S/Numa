"use client"

import { useState, useRef, useCallback, useLayoutEffect, useEffect } from "react"
import { createPortal } from "react-dom"
import { ChevronLeft, ChevronRight, X, Clock, Plus } from "lucide-react"

import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import { CalendarEvent, CalendarEventPayload } from "@/components/calendar/api"

type ViewMode = "month" | "week" | "day"

interface CalendarViewProps {
  events: CalendarEvent[]
  onCreateEvent?: (event: CalendarEventPayload) => Promise<void>
  onUpdateEvent?: (event: CalendarEvent) => Promise<void>
  onDeleteEvent?: (eventId: string) => Promise<void>
  onEditEvent?: (event: CalendarEvent) => void
}

const DAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
const MONTHS = [
  "January",
  "February",
  "March",
  "April",
  "May",
  "June",
  "July",
  "August",
  "September",
  "October",
  "November",
  "December",
]

const HOURS = Array.from({ length: 15 }, (_, i) => i + 7) // 7 AM - 9 PM
const SLOT_HEIGHT = 56
// Sidebar rail width (collapsed) in px - used to keep popups from hiding behind the sidebar
const SIDEBAR_RAIL_WIDTH = 56

function isSameDay(a: Date, b: Date) {
  return (
    a.getFullYear() === b.getFullYear() &&
    a.getMonth() === b.getMonth() &&
    a.getDate() === b.getDate()
  )
}

function getMonthGrid(year: number, month: number) {
  const first = new Date(year, month, 1)
  const last = new Date(year, month + 1, 0)
  const startDay = first.getDay()
  const days: (Date | null)[] = []
  for (let i = 0; i < startDay; i += 1) days.push(null)
  for (let d = 1; d <= last.getDate(); d += 1) days.push(new Date(year, month, d))
  while (days.length % 7 !== 0) days.push(null)
  return days
}

function getWeekDates(date: Date) {
  const start = new Date(date)
  start.setDate(start.getDate() - start.getDay())
  return Array.from({ length: 7 }, (_, i) => {
    const d = new Date(start)
    d.setDate(d.getDate() + i)
    return d
  })
}

function formatHour(hour: number) {
  if (hour > 12) return `${hour - 12}PM`
  if (hour === 12) return "12PM"
  return `${hour}AM`
}

function timeToMinutes(value: string) {
  const [h, m] = value.split(":").map(Number)
  return h * 60 + m
}

function minutesToTime(value: number) {
  const h = Math.floor(value / 60)
  const min = value % 60
  return `${String(h).padStart(2, "0")}:${String(min).padStart(2, "0")}`
}

function EventDetailPopup({
  event,
  anchorRect,
  onEdit,
  onDelete,
  onHoverStart,
  onHoverEnd,
  onClose,
}: {
  event: CalendarEvent
  anchorRect: {
    top: number
    right: number
    bottom: number
    left: number
    width: number
    height: number
  }
  onEdit?: (event: CalendarEvent) => void
  onDelete: (eventId: string) => Promise<void>
  onHoverStart: () => void
  onHoverEnd: () => void
  onClose: () => void
}) {
  const popupRef = useRef<HTMLDivElement>(null)
  const [coords, setCoords] = useState({ left: -9999, top: -9999 })

  useLayoutEffect(() => {
    const popup = popupRef.current
    if (!popup) {
      return
    }

    const rect = popup.getBoundingClientRect()
    const margin = 12
    const gap = 10
    // On desktop (lg) there's a sidebar rail of 56px; on mobile there's the 12px safe area.
    const leftBound = window.innerWidth >= 1024 ? SIDEBAR_RAIL_WIDTH + margin : margin

    const spaceRight = window.innerWidth - anchorRect.right
    const spaceLeft = anchorRect.left - leftBound
    const spaceBottom = window.innerHeight - anchorRect.bottom
    const spaceTop = anchorRect.top

    // Prefer to open to the right; fall back to left; otherwise center in available area
    let left: number
    if (spaceRight >= rect.width + gap) {
      left = anchorRect.right + gap
    } else if (spaceLeft >= rect.width + gap) {
      left = anchorRect.left - rect.width - gap
    } else {
      // Center between left bound and right edge
      left = leftBound + (window.innerWidth - leftBound - rect.width) / 2
    }

    let top = anchorRect.top + (anchorRect.height - rect.height) / 2

    if (top < margin && spaceBottom >= rect.height + gap) {
      top = anchorRect.bottom + gap
    } else if (top + rect.height > window.innerHeight - margin && spaceTop >= rect.height + gap) {
      top = anchorRect.top - rect.height - gap
    }

    // Clamp so popup never overlaps the sidebar or exits the viewport
    left = Math.max(leftBound, Math.min(left, window.innerWidth - rect.width - margin))
    top = Math.max(margin, Math.min(top, window.innerHeight - rect.height - margin))

    setCoords({ left, top })
  }, [anchorRect, event.id])

  const isSecondary = event.color === "secondary"
  const isReadonly = event.readonly

  return (
    <div
      ref={popupRef}
      className="fixed z-200"
      style={{ top: coords.top, left: coords.left }}
      onMouseEnter={onHoverStart}
      onMouseLeave={onHoverEnd}
    >
      <div className="w-72 rounded-xl border border-border/30 bg-card/95 p-4 shadow-lg backdrop-blur-md">
        <div className="mb-3 flex items-start justify-between">
          <div className={cn("h-1 w-10 rounded-full", isSecondary ? "bg-secondary" : "bg-primary")} />
          <button onClick={onClose} className="text-muted-foreground transition-colors hover:text-foreground">
            <X className="h-4 w-4" />
          </button>
        </div>
        <h3 className="mb-2 text-sm font-semibold text-foreground">{event.title}</h3>
        {event.calendarName && (
          <div className="mb-1 text-[11px] text-muted-foreground">Calendar: {event.calendarName}</div>
        )}
        <div className="mb-2 flex items-center gap-1.5 text-xs text-muted-foreground">
          <Clock className="h-3 w-3" />
          <span>
            {event.startTime} - {event.endTime}
          </span>
        </div>
        <p className="text-xs leading-relaxed text-muted-foreground/80">{event.description}</p>
        {!isReadonly && (
          <div className="mt-3 flex gap-2">
            <Button
              variant="outline"
              size="sm"
              className="flex-1"
              onClick={() => {
                onEdit?.(event)
                onClose()
              }}
            >
              Edit
            </Button>
            <Button
              variant="destructive"
              size="sm"
              className="flex-1"
              onClick={async () => {
                await onDelete(event.id)
                onClose()
              }}
            >
              Delete
            </Button>
          </div>
        )}
      </div>
    </div>
  )
}

function CreateEventPopup({
  date,
  hour,
  position,
  onClose,
  onCreate,
}: {
  date: Date
  hour: number
  position: { x: number; y: number }
  onClose: () => void
  onCreate: (event: CalendarEventPayload) => Promise<void>
}) {
  const [title, setTitle] = useState("")
  const [desc, setDesc] = useState("")
  const popupRef = useRef<HTMLDivElement>(null)
  const [coords, setCoords] = useState({ left: position.x, top: position.y })
  const startTime = `${String(hour).padStart(2, "0")}:00`
  const endTime = `${String(hour + 1).padStart(2, "0")}:00`

  useLayoutEffect(() => {
    const popup = popupRef.current
    if (!popup) return

    const rect = popup.getBoundingClientRect()
    const margin = 12
    const gap = 8
    const leftBound = window.innerWidth >= 1024 ? SIDEBAR_RAIL_WIDTH + margin : margin

    let left = position.x - rect.width / 2
    let top = position.y + gap

    if (top + rect.height > window.innerHeight - margin) {
      top = position.y - rect.height - gap
    }

    left = Math.max(leftBound, Math.min(left, window.innerWidth - rect.width - margin))
    top = Math.max(margin, Math.min(top, window.innerHeight - rect.height - margin))

    setCoords({ left, top })
  }, [position])

  const handleSubmit = async () => {
    if (!title.trim()) return

    await onCreate({
      title: title.trim(),
      date: date.toISOString().slice(0, 10),
      startTime,
      endTime,
      description: desc.trim() || "New event",
    })
    onClose()
  }

  return (
    <div ref={popupRef} className="fixed z-200" style={{ top: coords.top, left: coords.left }}>
      <div className="w-72 rounded-xl border border-border/30 bg-card/95 p-4 shadow-lg backdrop-blur-md">
        <div className="mb-3 flex items-center justify-between">
          <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
            <Plus className="h-3 w-3 text-primary" />
            <span className="text-sm font-semibold text-foreground">New Event</span>
          </div>
          <button onClick={onClose} className="text-muted-foreground transition-colors hover:text-foreground">
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="mb-3 flex items-center gap-1.5 text-[11px] text-muted-foreground">
          <Clock className="h-3 w-3" />
          <span>
            {startTime} - {endTime}
          </span>
        </div>

        <input
          autoFocus
          value={title}
          onChange={(event) => setTitle(event.target.value)}
          onKeyDown={(event) => event.key === "Enter" && handleSubmit()}
          placeholder="Event title"
          className="mb-2 w-full rounded-lg bg-muted/40 px-3 py-2 text-sm text-foreground transition-all placeholder:text-muted-foreground/50 focus:outline-none focus:ring-1 focus:ring-primary/40"
        />

        <input
          value={desc}
          onChange={(event) => setDesc(event.target.value)}
          onKeyDown={(event) => event.key === "Enter" && handleSubmit()}
          placeholder="Description (optional)"
          className="mb-3 w-full rounded-lg bg-muted/40 px-3 py-2 text-xs text-foreground transition-all placeholder:text-muted-foreground/50 focus:outline-none focus:ring-1 focus:ring-primary/40"
        />

        <Button size="sm" className="w-full" onClick={handleSubmit} disabled={!title.trim()}>
          Create Event
        </Button>
      </div>
    </div>
  )
}

function DayEventBlock({
  event,
  onDragEnd,
  onResizeEnd,
  onHover,
  onHoverEnd,
  onTap,
}: {
  event: CalendarEvent
  onDragEnd: (id: string, newStartMin: number) => void
  onResizeEnd: (id: string, newEndMin: number) => void
  onHover: (event: CalendarEvent, e: React.MouseEvent<HTMLElement>) => void
  onHoverEnd: () => void
  onTap?: () => void
}) {
  const startMin = timeToMinutes(event.startTime)
  const endMin = timeToMinutes(event.endTime)
  const duration = endMin - startMin
  const top = ((startMin - 7 * 60) / 60) * SLOT_HEIGHT
  const height = (duration / 60) * SLOT_HEIGHT

  const dragStartY = useRef(0)
  const resizeStartY = useRef(0)

  const isSecondary = event.color === "secondary"
  const isReadonly = event.readonly === true

  const handleDragStart = (e: React.MouseEvent) => {
    if (isReadonly) {
      return
    }

    e.stopPropagation()
    dragStartY.current = e.clientY
    const startMinOrig = startMin

    const onMove = () => {
      // Visual feedback is handled by hover styles.
    }

    const onUp = (mouseEvent: MouseEvent) => {
      const deltaY = mouseEvent.clientY - dragStartY.current
      const deltaMin = Math.round((deltaY / SLOT_HEIGHT) * 60 / 15) * 15
      const newStart = Math.max(7 * 60, Math.min(20 * 60, startMinOrig + deltaMin))
      onDragEnd(event.id, newStart)
      window.removeEventListener("mousemove", onMove)
      window.removeEventListener("mouseup", onUp)
    }

    window.addEventListener("mousemove", onMove)
    window.addEventListener("mouseup", onUp)
  }

  const handleResizeStart = (e: React.MouseEvent) => {
    if (isReadonly) {
      return
    }

    e.stopPropagation()
    resizeStartY.current = e.clientY
    const endMinOrig = endMin

    const onMove = () => {
      // Visual feedback is handled by hover styles.
    }

    const onUp = (mouseEvent: MouseEvent) => {
      const deltaY = mouseEvent.clientY - resizeStartY.current
      const deltaMin = Math.round((deltaY / SLOT_HEIGHT) * 60 / 15) * 15
      const newEnd = Math.max(startMin + 15, Math.min(21 * 60, endMinOrig + deltaMin))
      onResizeEnd(event.id, newEnd)
      window.removeEventListener("mousemove", onMove)
      window.removeEventListener("mouseup", onUp)
    }

    window.addEventListener("mousemove", onMove)
    window.addEventListener("mouseup", onUp)
  }

  return (
    <div
      className={cn(
        "group absolute left-0.5 right-0.5 cursor-grab overflow-hidden rounded-md border-0 border-l-2 px-2 py-1 transition-all duration-150 active:cursor-grabbing sm:px-2.5 sm:py-1.5",
        isReadonly && "cursor-default",
        onTap && "cursor-pointer",
        "bg-white/[0.05] hover:bg-white/[0.08]",
        isSecondary
          ? "border-l-secondary/70"
          : "border-l-primary/70"
      )}
      style={{ top, height: Math.max(height, 24), zIndex: 10 }}
      onMouseDown={handleDragStart}
      onMouseEnter={(e) => {
        e.stopPropagation()
        onHover(event, e)
      }}
      onMouseLeave={onHoverEnd}
      onClick={(e) => {
        if (onTap) {
          e.stopPropagation()
          onTap()
        }
      }}
    >
      <div className="truncate text-[11px] font-medium text-foreground sm:text-xs">{event.title}</div>
      {height >= 36 && <div className="text-[9px] text-muted-foreground sm:text-[10px]">{event.startTime} - {event.endTime}</div>}

      {!isReadonly && (
        <div
          className="absolute bottom-0 left-0 right-0 hidden h-2 cursor-s-resize items-center justify-center opacity-0 group-hover:flex group-hover:opacity-100"
          onMouseDown={handleResizeStart}
        >
          <div className="h-1 w-8 rounded-full bg-muted-foreground/30" />
        </div>
      )}
    </div>
  )
}

export default function CalendarView({
  events,
  onCreateEvent,
  onUpdateEvent,
  onDeleteEvent,
  onEditEvent,
}: CalendarViewProps) {
  const [view, setView] = useState<ViewMode>(() =>
    typeof window !== "undefined" && window.innerWidth < 640 ? "day" : "month"
  )
  const [currentDate, setCurrentDate] = useState(new Date())
  const [detailPopup, setDetailPopup] = useState<{
    event: CalendarEvent
    anchorRect: {
      top: number
      right: number
      bottom: number
      left: number
      width: number
      height: number
    }
  } | null>(null)
  const [createPopup, setCreatePopup] = useState<{
    date: Date
    hour: number
    pos: { x: number; y: number }
  } | null>(null)
  const closeTimerRef = useRef<number | null>(null)

  const [now, setNow] = useState(() => new Date())
  useEffect(() => {
    const id = window.setInterval(() => setNow(new Date()), 30_000)
    return () => window.clearInterval(id)
  }, [])

  // Responsive: detect mobile for layout adjustments
  const [isMobile, setIsMobile] = useState(() =>
    typeof window !== "undefined" ? window.innerWidth < 640 : false
  )
  useEffect(() => {
    const check = () => {
      const mobile = window.innerWidth < 640
      setIsMobile(mobile)
      if (mobile) {
        setView((current) => (current === "month" ? "day" : current))
      }
    }
    window.addEventListener("resize", check)
    return () => window.removeEventListener("resize", check)
  }, [])

  const today = now

  const navigate = (direction: number) => {
    const date = new Date(currentDate)
    if (view === "month") date.setMonth(date.getMonth() + direction)
    else if (view === "week") date.setDate(date.getDate() + direction * 7)
    else date.setDate(date.getDate() + direction)

    setCurrentDate(date)
    closePopups()
  }

  const closePopups = () => {
    setDetailPopup(null)
    setCreatePopup(null)
  }

  const cancelScheduledClose = useCallback(() => {
    if (closeTimerRef.current) {
      window.clearTimeout(closeTimerRef.current)
      closeTimerRef.current = null
    }
  }, [])

  const schedulePopupClose = useCallback(() => {
    cancelScheduledClose()
    closeTimerRef.current = window.setTimeout(() => {
      setDetailPopup(null)
    }, 130)
  }, [cancelScheduledClose])

  const eventsForDay = (date: Date) => events.filter((event) => isSameDay(event.date, date))

  const handleSlotClick = (date: Date, hour: number, event: React.MouseEvent) => {
    closePopups()
    setCreatePopup({ date, hour, pos: { x: event.clientX, y: event.clientY } })
  }

  const handleEventHover = useCallback(
    (event: CalendarEvent, mouseEvent: React.MouseEvent<HTMLElement>) => {
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
      if (existing?.readonly) {
        return
      }
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

      await onUpdateEvent({
        ...existing,
        endTime: minutesToTime(newEndMin),
      })
    },
    [events, onUpdateEvent]
  )

  const headerLabel =
    view === "month"
      ? `${MONTHS[currentDate.getMonth()]} ${currentDate.getFullYear()}`
      : view === "week"
        ? (() => {
            const week = getWeekDates(currentDate)
            return `${MONTHS[week[0].getMonth()]} ${week[0].getDate()} - ${week[6].getDate()}, ${week[6].getFullYear()}`
          })()
        : `${MONTHS[currentDate.getMonth()]} ${currentDate.getDate()}, ${currentDate.getFullYear()}`

  const nowMinutes = today.getHours() * 60 + today.getMinutes()
  const showNowLine = nowMinutes >= 7 * 60 && nowMinutes <= 22 * 60
  const nowTop = ((nowMinutes - 7 * 60) / 60) * SLOT_HEIGHT

  return (
    <div className="flex h-full flex-col" onClick={closePopups}>
      <div className="mb-2 flex flex-col gap-2 sm:mb-4 sm:flex-row sm:items-center sm:justify-between">
        <h2 className="truncate text-lg font-bold text-foreground sm:text-2xl">{headerLabel}</h2>
        <div className="flex items-center gap-1 sm:gap-2">
          <div className="flex gap-0.5 rounded-md border border-border/40 bg-card p-0.5">
            {(["month", "week", "day"] as ViewMode[]).map((mode) => (
              <button
                key={mode}
                onClick={(event) => {
                  event.stopPropagation()
                  setView(mode)
                  closePopups()
                }}
                className={cn(
                  "rounded-md px-2 py-1 text-xs font-medium capitalize transition-all sm:px-3 sm:py-1.5",
                  view === mode
                    ? "bg-primary text-primary-foreground"
                    : "text-muted-foreground hover:bg-accent/40 hover:text-foreground"
                )}
              >
                {isMobile ? mode.charAt(0).toUpperCase() : mode}
              </button>
            ))}
          </div>
          <Button variant="ghost" size="icon" className="h-8 w-8 sm:h-9 sm:w-9" onClick={() => navigate(-1)}>
            <ChevronLeft className="h-4 w-4" />
          </Button>
          <Button
            variant="ghost"
            size="sm"
            className="h-8 px-2 text-xs sm:h-9 sm:px-3 sm:text-sm"
            onClick={() => {
              setCurrentDate(new Date())
              closePopups()
            }}
          >
            Today
          </Button>
          <Button variant="ghost" size="icon" className="h-8 w-8 sm:h-9 sm:w-9" onClick={() => navigate(1)}>
            <ChevronRight className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {view === "month" && (
        <div className="flex-1 overflow-auto rounded-lg border border-border/40 bg-card/40 p-1 sm:rounded-xl sm:p-2">
          <div className="mb-1 grid grid-cols-7">
            {DAYS.map((day) => (
              <div key={day} className="py-1 text-center text-[10px] font-medium text-muted-foreground sm:py-2 sm:text-xs">
                {isMobile ? day.charAt(0) : day}
              </div>
            ))}
          </div>
          <div className="grid flex-1 grid-cols-7 gap-px">
            {getMonthGrid(currentDate.getFullYear(), currentDate.getMonth()).map((date, index) => {
              const dayEvents = date ? eventsForDay(date) : []
              const isToday = !!date && isSameDay(date, today)
              return (
                <div
                  key={index}
                  className={cn(
                    "min-h-12 rounded-md p-0.5 transition-all sm:min-h-20 sm:p-1.5",
                    date ? "cursor-pointer hover:bg-accent/30" : "opacity-0",
                    isToday && "bg-primary/10 ring-1 ring-primary/40"
                  )}
                  onClick={(event) => {
                    event.stopPropagation()
                    if (date) {
                      setCurrentDate(date)
                      setView("day")
                    }
                  }}
                >
                  {date && (
                    <>
                      <span
                        className={cn(
                          "text-[10px] font-medium sm:text-xs",
                          isToday ? "font-bold text-primary" : "text-muted-foreground"
                        )}
                      >
                        {date.getDate()}
                      </span>
                      <div className="mt-0.5 space-y-0.5">
                        {dayEvents.slice(0, isMobile ? 1 : 2).map((event) => (
                          <div
                            key={event.id}
                            onMouseEnter={(mouseEvent) => !isMobile && handleEventHover(event, mouseEvent)}
                            onMouseLeave={() => !isMobile && schedulePopupClose()}
                            onClick={(e) => {
                              e.stopPropagation()
                              if (isMobile) {
                                onEditEvent?.(event)
                              }
                            }}
                            className={cn(
                              "truncate rounded border px-1 py-0.5 text-[8px] font-medium transition-all hover:-translate-y-px sm:px-1.5 sm:text-[10px]",
                              event.color === "secondary"
                                ? "border-secondary/25 bg-secondary/15"
                                : "border-primary/25 bg-primary/15"
                            )}
                          >
                            {event.title}
                          </div>
                        ))}
                        {dayEvents.length > (isMobile ? 1 : 2) && (
                          <span className="text-[8px] text-muted-foreground sm:text-[10px]">+{dayEvents.length - (isMobile ? 1 : 2)} more</span>
                        )}
                      </div>
                    </>
                  )}
                </div>
              )
            })}
          </div>
        </div>
      )}

      {view === "week" && (
        <div className="flex-1 overflow-auto rounded-lg border border-border/40 bg-card/40 p-1 sm:rounded-xl sm:p-2">
          <div className="grid min-w-[500px] grid-cols-[40px_repeat(7,1fr)] gap-px sm:grid-cols-[50px_repeat(7,1fr)]">
            <div />
            {getWeekDates(currentDate).map((date, index) => (
              <div
                key={index}
                className={cn(
                  "py-1 text-center text-[10px] font-medium sm:py-2 sm:text-xs",
                  isSameDay(date, today) ? "text-primary" : "text-muted-foreground"
                )}
              >
                <div>{isMobile ? DAYS[date.getDay()].charAt(0) : DAYS[date.getDay()]}</div>
                <div
                  className={cn(
                    "text-sm font-bold sm:text-lg",
                    isSameDay(date, today) ? "text-primary" : "text-foreground"
                  )}
                >
                  {date.getDate()}
                </div>
              </div>
            ))}

            {HOURS.map((hour) => (
              <div key={`row-${hour}`} className="contents">
                <div className="pr-1 pt-1 text-right text-[8px] text-muted-foreground sm:pr-2 sm:text-[10px]">{formatHour(hour)}</div>
                {getWeekDates(currentDate).map((date, dayIndex) => (
                  <div
                    key={`${hour}-${dayIndex}`}
                    className="relative min-h-10 cursor-pointer border-t border-border/20 p-0.5 transition-colors hover:bg-accent/10 sm:min-h-12"
                    onClick={(event) => handleSlotClick(date, hour, event)}
                  >
                    {eventsForDay(date)
                      .filter((calendarEvent) => parseInt(calendarEvent.startTime, 10) === hour)
                      .map((calendarEvent) => (
                        <div
                          key={calendarEvent.id}
                          onMouseEnter={(mouseEvent) => !isMobile && handleEventHover(calendarEvent, mouseEvent)}
                          onMouseLeave={() => !isMobile && schedulePopupClose()}
                          onClick={(e) => {
                            e.stopPropagation()
                            if (isMobile) {
                              onEditEvent?.(calendarEvent)
                            }
                          }}
                          className={cn(
                            "cursor-pointer rounded border px-1 py-0.5 text-[8px] font-medium transition-all hover:-translate-y-px sm:px-1.5 sm:py-1 sm:text-[10px]",
                            calendarEvent.color === "secondary"
                              ? "border-secondary/25 bg-secondary/15"
                              : "border-primary/25 bg-primary/15"
                          )}
                        >
                          <div className="truncate">{calendarEvent.title}</div>
                          <div className="hidden text-muted-foreground sm:block">{calendarEvent.startTime}</div>
                        </div>
                      ))}
                  </div>
                ))}
              </div>
            ))}
          </div>
        </div>
      )}

      {view === "day" && (
        <div className="relative flex-1 overflow-auto rounded-lg border border-white/[0.06] bg-black p-0 sm:rounded-xl">
          <div className="grid grid-cols-[44px_1fr] sm:grid-cols-[52px_1fr]">
            {/* Hour labels column */}
            <div className="relative" style={{ height: HOURS.length * SLOT_HEIGHT }}>
              {HOURS.map((hour) => (
                <div
                  key={hour}
                  className="absolute w-full pr-2 text-right text-[9px] text-white/25 sm:text-[10px]"
                  style={{ top: (hour - 7) * SLOT_HEIGHT - 7 }}
                >
                  {formatHour(hour)}
                </div>
              ))}
            </div>
            {/* Event column */}
            <div className="relative border-l border-white/[0.06]" style={{ height: HOURS.length * SLOT_HEIGHT }}>
              {HOURS.map((hour) => (
                <div
                  key={hour}
                  className="absolute left-0 right-0 cursor-pointer border-t border-white/[0.06] transition-colors hover:bg-white/[0.02]"
                  style={{ top: (hour - 7) * SLOT_HEIGHT, height: SLOT_HEIGHT }}
                  onClick={(event) => handleSlotClick(currentDate, hour, event)}
                />
              ))}

              {showNowLine && isSameDay(currentDate, today) && (
                <div className="absolute left-0 right-0 z-20 flex items-center" style={{ top: nowTop }}>
                  <div className="h-1.5 w-1.5 rounded-full bg-red-500" />
                  <div className="h-px flex-1 bg-red-500/50" />
                </div>
              )}

              {eventsForDay(currentDate).map((event) => (
                <DayEventBlock
                  key={event.id}
                  event={event}
                  onDragEnd={handleDragEnd}
                  onResizeEnd={handleResizeEnd}
                  onHover={handleEventHover}
                  onHoverEnd={schedulePopupClose}
                  onTap={isMobile ? () => onEditEvent?.(event) : undefined}
                />
              ))}
            </div>
          </div>
        </div>
      )}

      {detailPopup &&
        createPortal(
          <EventDetailPopup
            event={detailPopup.event}
            anchorRect={detailPopup.anchorRect}
            onEdit={onEditEvent}
            onDelete={handleDelete}
            onHoverStart={cancelScheduledClose}
            onHoverEnd={schedulePopupClose}
            onClose={closePopups}
          />,
          document.body
        )}

      {createPopup &&
        createPortal(
          <CreateEventPopup
            date={createPopup.date}
            hour={createPopup.hour}
            position={createPopup.pos}
            onClose={closePopups}
            onCreate={handleCreate}
          />,
          document.body
        )}
    </div>
  )
}
