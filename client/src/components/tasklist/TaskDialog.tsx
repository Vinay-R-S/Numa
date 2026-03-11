"use client"

import React, { useState } from "react"
import { useForm } from "react-hook-form"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Label } from "@/components/ui/label"
import { Button } from "@/components/ui/button"
import { DatePicker } from "@/components/ui/date-picker"
import { TimePicker } from "@/components/ui/time-picker"
import type { Task, TaskStatus, TaskPriority } from "./types"

interface TaskDialogProps {
  open: boolean
  onClose: () => void
  onSave: (data: Partial<Task> & { title: string }) => Promise<void>
  task?: Task | null
  defaultStatus?: TaskStatus
}

type FormValues = {
  title: string
  description: string
  status: TaskStatus
  priority: TaskPriority | ""
  due_date: string
  due_time: string
  reminder_at: string
  reminder_time: string
}

function toLocalDateString(iso: string | null | undefined): string {
  if (!iso) return ""
  const d = new Date(iso)
  return d.toISOString().slice(0, 10)
}

function toLocalTimeString(iso: string | null | undefined): string {
  if (!iso) return ""
  const d = new Date(iso)
  return d.toTimeString().slice(0, 5)
}

function combineDatetime(date: string, time: string): string | null {
  if (!date) return null
  const t = time || "00:00"
  return new Date(`${date}T${t}`).toISOString()
}

export function TaskDialog({
  open,
  onClose,
  onSave,
  task,
  defaultStatus = "planned",
}: TaskDialogProps) {
  const [saving, setSaving] = useState(false)

  const { register, handleSubmit, setValue, watch, reset } = useForm<FormValues>({
    defaultValues: {
      title: task?.title ?? "",
      description: task?.description ?? "",
      status: task?.status ?? defaultStatus,
      priority: task?.priority ?? "",
      due_date: toLocalDateString(task?.due_date),
      due_time: toLocalTimeString(task?.due_date),
      reminder_at: toLocalDateString(task?.reminder_at),
      reminder_time: toLocalTimeString(task?.reminder_at),
    },
  })

  // Reset form when task changes or dialog opens
  React.useEffect(() => {
    if (open) {
      reset({
        title: task?.title ?? "",
        description: task?.description ?? "",
        status: task?.status ?? defaultStatus,
        priority: task?.priority ?? "",
        due_date: toLocalDateString(task?.due_date),
        due_time: toLocalTimeString(task?.due_date),
        reminder_at: toLocalDateString(task?.reminder_at),
        reminder_time: toLocalTimeString(task?.reminder_at),
      })
    }
  }, [open, task, defaultStatus, reset])

  const statusValue = watch("status")
  const priorityValue = watch("priority")

  const onSubmit = async (values: FormValues) => {
    setSaving(true)
    try {
      await onSave({
        title: values.title,
        description: values.description || null,
        status: values.status,
        priority: (values.priority as TaskPriority) || null,
        due_date: combineDatetime(values.due_date, values.due_time),
        reminder_at: combineDatetime(values.reminder_at, values.reminder_time),
        source_name: task?.source_name ?? null,
        source_logo: task?.source_logo ?? null,
      })
      onClose()
    } finally {
      setSaving(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>{task ? "Edit Task" : "New Task"}</DialogTitle>
        </DialogHeader>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          {/* Title */}
          <div className="space-y-1.5">
            <Label htmlFor="title">Task Name *</Label>
            <Input
              id="title"
              placeholder="What needs to be done?"
              {...register("title", { required: true })}
            />
          </div>

          {/* Description */}
          <div className="space-y-1.5">
            <Label htmlFor="description">Description</Label>
            <Textarea
              id="description"
              placeholder="Add more details…"
              rows={3}
              {...register("description")}
            />
          </div>

          {/* Status + Priority */}
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label>Status</Label>
              <Select
                value={statusValue}
                onValueChange={(v) => setValue("status", v as TaskStatus)}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="planned">Planned</SelectItem>
                  <SelectItem value="inprogress">In Progress</SelectItem>
                  <SelectItem value="completed">Completed</SelectItem>
                  <SelectItem value="pending">Pending</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-1.5">
              <Label>Priority</Label>
              <Select
                value={priorityValue || "none"}
                onValueChange={(v) =>
                  setValue("priority", v === "none" ? "" : (v as TaskPriority))
                }
              >
                <SelectTrigger>
                  <SelectValue placeholder="None" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="none">None</SelectItem>
                  <SelectItem value="low">🟦 Low</SelectItem>
                  <SelectItem value="medium">🟦 Medium</SelectItem>
                  <SelectItem value="high">🟧 High</SelectItem>
                  <SelectItem value="urgent">🔴 Urgent</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          {/* Due Date + Time */}
          <div className="space-y-1.5">
            <Label>Due Date &amp; Time</Label>
            <div className="grid grid-cols-2 gap-2">
              <DatePicker
                value={watch("due_date")}
                onChange={(v) => setValue("due_date", v)}
                placeholder="Due date"
              />
              <TimePicker
                value={watch("due_time")}
                onChange={(v) => setValue("due_time", v)}
                placeholder="Due time"
              />
            </div>
          </div>

          {/* Reminder */}
          <div className="space-y-1.5">
            <Label>Reminder</Label>
            <div className="grid grid-cols-2 gap-2">
              <DatePicker
                value={watch("reminder_at")}
                onChange={(v) => setValue("reminder_at", v)}
                placeholder="Reminder date"
              />
              <TimePicker
                value={watch("reminder_time")}
                onChange={(v) => setValue("reminder_time", v)}
                placeholder="Reminder time"
              />
            </div>
            <p className="text-xs text-muted-foreground">
              Browser notification will fire at this time.
            </p>
          </div>

          <DialogFooter>
            <Button type="button" variant="ghost" onClick={onClose}>
              Cancel
            </Button>
            <Button type="submit" disabled={saving}>
              {saving ? "Saving…" : task ? "Save Changes" : "Create Task"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
