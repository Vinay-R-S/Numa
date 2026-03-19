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

const HOURS = Array.from({ length: 14 }, (_, i) => i + 7)
const SLOT_HEIGHT = 56

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

    const spaceRight = window.innerWidth - anchorRect.right
    const spaceLeft = anchorRect.left
    const spaceBottom = window.innerHeight - anchorRect.bottom
    const spaceTop = anchorRect.top

    let left =
      spaceRight >= rect.width + gap
        ? anchorRect.right + gap
        : spaceLeft >= rect.width + gap
          ? anchorRect.left - rect.width - gap
          : Math.max(margin, Math.min(anchorRect.left, window.innerWidth - rect.width - margin))

    let top = anchorRect.top + (anchorRect.height - rect.height) / 2

    if (top < margin && spaceBottom >= rect.height + gap) {
      top = anchorRect.bottom + gap
    } else if (top + rect.height > window.innerHeight - margin && spaceTop >= rect.height + gap) {
      top = anchorRect.top - rect.height - gap
    }

    left = Math.max(margin, Math.min(left, window.innerWidth - rect.width - margin))
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
          <Button
            variant="outline"
            size="sm"
            className="mt-3 w-full"
            onClick={async () => {
              await onDelete(event.id)
              onClose()
            }}
          >
            Delete Event
          </Button>
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

    let left = position.x - rect.width / 2
    let top = position.y + gap

    if (top + rect.height > window.innerHeight - margin) {
      top = position.y - rect.height - gap
    }

    left = Math.max(margin, Math.min(left, window.innerWidth - rect.width - margin))
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
}: {
  event: CalendarEvent
  onDragEnd: (id: string, newStartMin: number) => void
  onResizeEnd: (id: string, newEndMin: number) => void
  onHover: (event: CalendarEvent, e: React.MouseEvent<HTMLElement>) => void
  onHoverEnd: () => void
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
        "group absolute left-1 right-1 cursor-grab rounded-lg border px-2.5 py-1.5 transition-all duration-200 active:cursor-grabbing",
        isReadonly && "cursor-default",
        "hover:-translate-y-px hover:shadow-lg",
        isSecondary
          ? "border-secondary/20 bg-linear-to-br from-secondary/25 to-primary/10 hover:border-secondary/50"
          : "border-primary/20 bg-linear-to-br from-primary/25 to-secondary/10 hover:border-primary/50"
      )}
      style={{ top, height: Math.max(height, 24), zIndex: 10 }}
      onMouseDown={handleDragStart}
      onMouseEnter={(e) => {
        e.stopPropagation()
        onHover(event, e)
      }}
      onMouseLeave={onHoverEnd}
    >
      <div className="truncate text-xs font-medium text-foreground">{event.title}</div>
      {height >= 36 && <div className="text-[10px] text-muted-foreground">{event.startTime} - {event.endTime}</div>}

      {!isReadonly && (
        <div
          className="absolute bottom-0 left-0 right-0 flex h-2 cursor-s-resize items-center justify-center opacity-0 group-hover:opacity-100"
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
}: CalendarViewProps) {
  const [view, setView] = useState<ViewMode>("month")
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
  const showNowLine = nowMinutes >= 7 * 60 && nowMinutes <= 21 * 60
  const nowTop = ((nowMinutes - 7 * 60) / 60) * SLOT_HEIGHT

  return (
    <div className="flex h-full flex-col" onClick={closePopups}>
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-2xl font-bold text-foreground">{headerLabel}</h2>
        <div className="flex items-center gap-2">
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
                  "rounded-md px-3 py-1.5 text-xs font-medium capitalize transition-all",
                  view === mode
                    ? "bg-primary text-primary-foreground"
                    : "text-muted-foreground hover:bg-accent/40 hover:text-foreground"
                )}
              >
                {mode}
              </button>
            ))}
          </div>
          <Button variant="ghost" size="icon" onClick={() => navigate(-1)}>
            <ChevronLeft className="h-4 w-4" />
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => {
              setCurrentDate(new Date())
              closePopups()
            }}
          >
            Today
          </Button>
          <Button variant="ghost" size="icon" onClick={() => navigate(1)}>
            <ChevronRight className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {view === "month" && (
        <div className="flex-1 rounded-xl border border-border/40 bg-card/40 p-2">
          <div className="mb-1 grid grid-cols-7">
            {DAYS.map((day) => (
              <div key={day} className="py-2 text-center text-xs font-medium text-muted-foreground">
                {day}
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
                    "min-h-20 rounded-md p-1.5 transition-all",
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
                          "text-xs font-medium",
                          isToday ? "font-bold text-primary" : "text-muted-foreground"
                        )}
                      >
                        {date.getDate()}
                      </span>
                      <div className="mt-0.5 space-y-0.5">
                        {dayEvents.slice(0, 2).map((event) => (
                          <div
                            key={event.id}
                            onMouseEnter={(mouseEvent) => handleEventHover(event, mouseEvent)}
                            onMouseLeave={schedulePopupClose}
                            className={cn(
                              "truncate rounded border px-1.5 py-0.5 text-[10px] font-medium transition-all hover:-translate-y-px",
                              event.color === "secondary"
                                ? "border-secondary/20 bg-linear-to-r from-secondary/25 to-primary/15"
                                : "border-primary/20 bg-linear-to-r from-primary/25 to-secondary/15"
                            )}
                          >
                            {event.title}
                          </div>
                        ))}
                        {dayEvents.length > 2 && (
                          <span className="text-[10px] text-muted-foreground">+{dayEvents.length - 2} more</span>
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
        <div className="flex-1 overflow-auto rounded-xl border border-border/40 bg-card/40 p-2">
          <div className="grid grid-cols-[50px_repeat(7,1fr)] gap-px">
            <div />
            {getWeekDates(currentDate).map((date, index) => (
              <div
                key={index}
                className={cn(
                  "py-2 text-center text-xs font-medium",
                  isSameDay(date, today) ? "text-primary" : "text-muted-foreground"
                )}
              >
                <div>{DAYS[date.getDay()]}</div>
                <div
                  className={cn(
                    "text-lg font-bold",
                    isSameDay(date, today) ? "text-primary" : "text-foreground"
                  )}
                >
                  {date.getDate()}
                </div>
              </div>
            ))}

            {HOURS.map((hour) => (
              <div key={`row-${hour}`} className="contents">
                <div className="pr-2 pt-1 text-right text-[10px] text-muted-foreground">{formatHour(hour)}</div>
                {getWeekDates(currentDate).map((date, dayIndex) => (
                  <div
                    key={`${hour}-${dayIndex}`}
                    className="relative min-h-12 cursor-pointer border-t border-border/20 p-0.5 transition-colors hover:bg-accent/10"
                    onClick={(event) => handleSlotClick(date, hour, event)}
                  >
                    {eventsForDay(date)
                      .filter((calendarEvent) => parseInt(calendarEvent.startTime, 10) === hour)
                      .map((calendarEvent) => (
                        <div
                          key={calendarEvent.id}
                          onMouseEnter={(mouseEvent) => handleEventHover(calendarEvent, mouseEvent)}
                          onMouseLeave={schedulePopupClose}
                          className={cn(
                            "cursor-pointer rounded border px-1.5 py-1 text-[10px] font-medium transition-all hover:-translate-y-px",
                            calendarEvent.color === "secondary"
                              ? "border-secondary/20 bg-linear-to-r from-secondary/25 to-primary/15"
                              : "border-primary/20 bg-linear-to-r from-primary/25 to-secondary/15"
                          )}
                        >
                          <div className="truncate">{calendarEvent.title}</div>
                          <div className="text-muted-foreground">{calendarEvent.startTime}</div>
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
        <div className="flex-1 overflow-auto rounded-xl border border-border/40 bg-card/40 p-2">
          <div className="grid grid-cols-[50px_1fr] gap-px">
            <div className="relative" style={{ height: HOURS.length * SLOT_HEIGHT }}>
              {HOURS.map((hour) => (
                <div
                  key={hour}
                  className="absolute w-full pr-2 text-right text-[10px] text-muted-foreground"
                  style={{ top: (hour - 7) * SLOT_HEIGHT }}
                >
                  {formatHour(hour)}
                </div>
              ))}
            </div>
            <div className="relative" style={{ height: HOURS.length * SLOT_HEIGHT }}>
              {HOURS.map((hour) => (
                <div
                  key={hour}
                  className="absolute left-0 right-0 h-14 cursor-pointer border-t border-border/15 transition-colors hover:bg-accent/10"
                  style={{ top: (hour - 7) * SLOT_HEIGHT }}
                  onClick={(event) => handleSlotClick(currentDate, hour, event)}
                />
              ))}

              {showNowLine && isSameDay(currentDate, today) && (
                <div className="absolute left-0 right-0 z-20 flex items-center" style={{ top: nowTop }}>
                  <div className="h-2 w-2 rounded-full bg-destructive" />
                  <div className="h-px flex-1 bg-destructive/60" />
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
