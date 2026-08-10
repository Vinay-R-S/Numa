"use client"

import { useLayoutEffect, useRef, useState } from "react"
import { Clock, Plus, X } from "lucide-react"

import { Button } from "@/components/ui/button"
import { calendarEventUpsertSchema } from "../calendar.schema"
import { createPopupPosition, toDateParam } from "../calendar.utils"
import type { CalendarEventPayload, Point } from "../calendar.types"

interface CreateEventPopupProps {
  date: Date
  hour: number
  position: Point
  onClose: () => void
  onCreate: (event: CalendarEventPayload) => Promise<void>
}

export function CreateEventPopup({ date, hour, position, onClose, onCreate }: CreateEventPopupProps) {
  const [title, setTitle] = useState("")
  const [description, setDescription] = useState("")
  const [error, setError] = useState<string | null>(null)
  const popupRef = useRef<HTMLDivElement>(null)
  const [coords, setCoords] = useState({ left: position.x, top: position.y })

  const startTime = `${String(hour).padStart(2, "0")}:00`
  const endTime = `${String(hour + 1).padStart(2, "0")}:00`

  useLayoutEffect(() => {
    const popup = popupRef.current
    if (!popup) return

    const rect = popup.getBoundingClientRect()
    const { x, y } = createPopupPosition(
      position,
      { width: rect.width, height: rect.height },
      { width: globalThis.innerWidth, height: globalThis.innerHeight }
    )
    setCoords({ left: x, top: y })
  }, [position])

  const handleSubmit = async () => {
    const parsed = calendarEventUpsertSchema.safeParse({
      title,
      date: toDateParam(date),
      startTime,
      endTime,
      description: description.trim() || "New event",
    })

    if (!parsed.success) {
      setError(parsed.error.issues[0]?.message ?? "Check the event details")
      return
    }

    setError(null)
    await onCreate(parsed.data)
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
          value={description}
          onChange={(event) => setDescription(event.target.value)}
          onKeyDown={(event) => event.key === "Enter" && handleSubmit()}
          placeholder="Description (optional)"
          className="mb-3 w-full rounded-lg bg-muted/40 px-3 py-2 text-xs text-foreground transition-all placeholder:text-muted-foreground/50 focus:outline-none focus:ring-1 focus:ring-primary/40"
        />

        {error && <p className="mb-2 text-[11px] text-destructive">{error}</p>}

        <Button size="sm" className="w-full" onClick={handleSubmit} disabled={!title.trim()}>
          Create Event
        </Button>
      </div>
    </div>
  )
}
