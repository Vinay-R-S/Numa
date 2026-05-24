"use client"

import { useState } from "react"
import { X, Calendar } from "lucide-react"
import { Button } from "@/components/ui/button"
import { CalendarEvent } from "@/components/calendar/api"

interface EventEditDialogProps {
  event: CalendarEvent
  onClose: () => void
  onSave: (event: CalendarEvent) => Promise<void>
  onDelete: (eventId: string) => Promise<void>
}

export function EventEditDialog({ event, onClose, onSave, onDelete }: EventEditDialogProps) {
  const [title, setTitle] = useState(event.title)
  const [description, setDescription] = useState(event.description)
  const [date, setDate] = useState(event.date.toISOString().slice(0, 10))
  const [startTime, setStartTime] = useState(event.startTime)
  const [endTime, setEndTime] = useState(event.endTime)
  const [loading, setLoading] = useState(false)

  const handleSave = async () => {
    if (!title.trim() || loading) return

    setLoading(true)
    try {
      await onSave({
        ...event,
        title: title.trim(),
        description: description.trim(),
        date: new Date(date),
        startTime,
        endTime,
      })
      onClose()
    } catch (error) {
      console.error("Failed to save event:", error)
    } finally {
      setLoading(false)
    }
  }

  const handleDelete = async () => {
    if (loading) return
    if (!confirm("Are you sure you want to delete this event?")) return

    setLoading(true)
    try {
      await onDelete(event.id)
      onClose()
    } catch (error) {
      console.error("Failed to delete event:", error)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 z-[300] flex items-center justify-center bg-black/50 backdrop-blur-sm">
      <div className="w-full max-w-md rounded-2xl border border-border/40 bg-card/95 p-6 shadow-2xl backdrop-blur-md">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-foreground">Edit Event</h2>
          <button
            onClick={onClose}
            className="text-muted-foreground transition-colors hover:text-foreground"
            disabled={loading}
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="space-y-4">
          {event.calendarName && (
            <div className="flex items-center gap-2 rounded-lg bg-muted/40 px-3 py-2 text-xs text-muted-foreground">
              <Calendar className="h-3 w-3" />
              <span>Calendar: {event.calendarName}</span>
            </div>
          )}

          <div>
            <label className="mb-1.5 block text-xs font-medium text-muted-foreground">Title</label>
            <input
              autoFocus
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Event title"
              className="w-full rounded-lg border border-border/40 bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground/50 focus:outline-none focus:ring-2 focus:ring-primary/30"
              disabled={loading}
            />
          </div>

          <div>
            <label className="mb-1.5 block text-xs font-medium text-muted-foreground">Description</label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Add description (optional)"
              rows={3}
              className="w-full resize-none rounded-lg border border-border/40 bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground/50 focus:outline-none focus:ring-2 focus:ring-primary/30"
              disabled={loading}
            />
          </div>

          <div>
            <label className="mb-1.5 block text-xs font-medium text-muted-foreground">Date</label>
            <input
              type="date"
              value={date}
              onChange={(e) => setDate(e.target.value)}
              className="w-full rounded-lg border border-border/40 bg-background px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/30"
              disabled={loading}
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="mb-1.5 block text-xs font-medium text-muted-foreground">Start Time</label>
              <input
                type="time"
                value={startTime}
                onChange={(e) => setStartTime(e.target.value)}
                className="w-full rounded-lg border border-border/40 bg-background px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/30"
                disabled={loading}
              />
            </div>
            <div>
              <label className="mb-1.5 block text-xs font-medium text-muted-foreground">End Time</label>
              <input
                type="time"
                value={endTime}
                onChange={(e) => setEndTime(e.target.value)}
                className="w-full rounded-lg border border-border/40 bg-background px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/30"
                disabled={loading}
              />
            </div>
          </div>

          <div className="flex gap-2 pt-2">
            <Button
              variant="outline"
              className="flex-1"
              onClick={onClose}
              disabled={loading}
            >
              Cancel
            </Button>
            {!event.readonly && (
              <Button
                variant="destructive"
                onClick={handleDelete}
                disabled={loading}
              >
                Delete
              </Button>
            )}
            <Button
              className="flex-1"
              onClick={handleSave}
              disabled={!title.trim() || loading}
            >
              {loading ? "Saving..." : "Save"}
            </Button>
          </div>
        </div>
      </div>
    </div>
  )
}
