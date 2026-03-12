"use client"

import React from "react"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import {
  Calendar,
  Clock,
  AlertCircle,
  Pencil,
  ExternalLink,
  CheckCircle2,
  Hash,
} from "lucide-react"
import { format, isPast, isToday } from "date-fns"
import type { Task } from "./types"
import { PRIORITY_CONFIG, COLUMN_CONFIG } from "./types"
import { cn } from "@/lib/utils"

interface TaskDetailSheetProps {
  task: Task | null
  open: boolean
  onClose: () => void
  /** If provided, an "Edit" button is shown */
  onEdit?: (task: Task) => void
}

function MetaRow({
  label,
  children,
}: {
  label: string
  children: React.ReactNode
}) {
  return (
    <div className="flex flex-col gap-0.5">
      <span className="text-[10px] uppercase tracking-wider text-muted-foreground font-semibold">
        {label}
      </span>
      <span className="text-sm font-medium text-foreground">{children}</span>
    </div>
  )
}

export function TaskDetailSheet({
  task,
  open,
  onClose,
  onEdit,
}: TaskDetailSheetProps) {
  if (!task) return null

  const priorityCfg = task.priority ? PRIORITY_CONFIG[task.priority] : null
  const statusCfg = COLUMN_CONFIG[task.status]
  const dueDate = task.due_date ? new Date(task.due_date) : null
  const isDue = dueDate && isPast(dueDate) && task.status !== "completed"
  const isDueToday = dueDate && isToday(dueDate)

  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="max-w-md flex flex-col max-h-[90dvh]">
        <DialogHeader className="shrink-0">
          {/* Source */}
          {(task.source_name || task.source_logo) && (
            <div className="flex items-center gap-1.5 mb-1">
              {task.source_logo && (
                <img
                  src={task.source_logo}
                  alt={task.source_name ?? ""}
                  className="h-4 w-4 rounded-sm object-contain"
                  onError={(e) => {
                    ;(e.target as HTMLImageElement).style.display = "none"
                  }}
                />
              )}
              {task.source_name && (
                <span className="text-xs text-muted-foreground flex items-center gap-1">
                  {task.source_name}
                  <ExternalLink className="h-3 w-3" />
                </span>
              )}
            </div>
          )}
          <DialogTitle className="text-lg leading-snug pr-2">
            {task.title}
          </DialogTitle>
        </DialogHeader>

        <div className="flex-1 overflow-y-auto space-y-4 pr-1">
          {/* Status + Priority badges */}
          <div className="flex flex-wrap gap-2">
            <span
              className={cn(
                "inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-semibold",
                statusCfg.bgColor,
                statusCfg.color
              )}
            >
              <span
                className={cn("h-1.5 w-1.5 rounded-full", {
                  "bg-blue-400": task.status === "planned",
                  "bg-amber-400": task.status === "inprogress",
                  "bg-emerald-400": task.status === "completed",
                  "bg-rose-400": task.status === "pending",
                })}
              />
              {statusCfg.label}
            </span>

            {priorityCfg && (
              <span
                className={cn(
                  "inline-flex items-center gap-1.5 rounded-full border border-white/10 px-2.5 py-1 text-xs font-semibold",
                  priorityCfg.color
                )}
              >
                <span className={cn("h-1.5 w-1.5 rounded-full", priorityCfg.dot)} />
                {priorityCfg.label}
              </span>
            )}
          </div>

          {/* Description */}
          {task.description && (
            <div className="rounded-xl border border-border/40 bg-muted/20 p-3.5 text-sm text-muted-foreground leading-relaxed whitespace-pre-wrap">
              {task.description}
            </div>
          )}

          {/* Meta grid */}
          <div className="grid grid-cols-2 gap-x-4 gap-y-3">
            {dueDate && (
              <MetaRow label="Due Date">
                <span
                  className={cn(
                    "flex items-center gap-1",
                    isDue
                      ? "text-red-400"
                      : isDueToday
                      ? "text-amber-400"
                      : "text-foreground"
                  )}
                >
                  {isDue ? (
                    <AlertCircle className="h-3.5 w-3.5" />
                  ) : (
                    <Calendar className="h-3.5 w-3.5 opacity-60" />
                  )}
                  {format(dueDate, "MMM d, yyyy")}
                  {dueDate.getHours() !== 0 || dueDate.getMinutes() !== 0
                    ? `, ${format(dueDate, "h:mm a")}`
                    : ""}
                </span>
              </MetaRow>
            )}

            {task.reminder_at && (
              <MetaRow label="Reminder">
                <span className="flex items-center gap-1 text-violet-400">
                  <Clock className="h-3.5 w-3.5" />
                  {format(new Date(task.reminder_at), "MMM d, h:mm a")}
                </span>
              </MetaRow>
            )}

            {task.completed_at && (
              <MetaRow label="Completed">
                <span className="flex items-center gap-1 text-emerald-400">
                  <CheckCircle2 className="h-3.5 w-3.5" />
                  {format(new Date(task.completed_at), "MMM d, yyyy")}
                </span>
              </MetaRow>
            )}

            <MetaRow label="Created">
              {format(new Date(task.created_at), "MMM d, yyyy")}
            </MetaRow>

            <MetaRow label="Last Updated">
              {format(new Date(task.updated_at), "MMM d, yyyy")}
            </MetaRow>

            <MetaRow label="Task ID">
              <span className="flex items-center gap-1 text-muted-foreground font-mono text-xs">
                <Hash className="h-3 w-3" />
                {task.id.slice(0, 8)}…
              </span>
            </MetaRow>
          </div>
        </div>

        <DialogFooter className="shrink-0 pt-4">
          <Button variant="ghost" onClick={onClose}>
            Close
          </Button>
          {onEdit && (
            <Button
              onClick={() => {
                onClose()
                onEdit(task)
              }}
            >
              <Pencil className="h-3.5 w-3.5 mr-1.5" />
              Edit
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
