"use client"

import React from "react"
import {
  Calendar,
  Clock,
  AlertCircle,
  Grip,
  Pencil,
  Trash2,
  ExternalLink,
} from "lucide-react"
import { useSortable } from "@dnd-kit/sortable"
import { CSS } from "@dnd-kit/utilities"
import { format, isPast, isToday } from "date-fns"
import type { Task } from "./types"
import { PRIORITY_CONFIG } from "./types"
import { cn } from "@/lib/utils"

interface TaskCardProps {
  task: Task
  onEdit: (task: Task) => void
  onDelete: (id: string) => void
  overlay?: boolean
}

export function TaskCard({ task, onEdit, onDelete, overlay }: TaskCardProps) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: task.id })

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  }

  const priorityCfg = task.priority ? PRIORITY_CONFIG[task.priority] : null
  const dueDate = task.due_date ? new Date(task.due_date) : null
  const isDue = dueDate && isPast(dueDate) && task.status !== "completed"
  const isDueToday = dueDate && isToday(dueDate)

  return (
    <div
      ref={setNodeRef}
      style={style}
      className={cn(
        "group relative rounded-xl border border-border/50 bg-card p-3.5 shadow-sm",
        "transition-all duration-200 hover:border-border hover:shadow-md",
        isDragging && "opacity-40",
        overlay && "shadow-2xl border-border rotate-2 scale-105",
      )}
    >
      {/* Drag Handle */}
      <div
        {...attributes}
        {...listeners}
        className="absolute left-2 top-1/2 -translate-y-1/2 cursor-grab opacity-0 group-hover:opacity-40 active:cursor-grabbing transition-opacity"
      >
        <Grip className="h-4 w-4 text-muted-foreground" />
      </div>

      {/* Actions */}
      <div className="absolute right-2 top-2 flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
        <button
          onClick={() => onEdit(task)}
          className="rounded-md p-1 text-muted-foreground hover:bg-accent hover:text-foreground transition-colors"
        >
          <Pencil className="h-3.5 w-3.5" />
        </button>
        <button
          onClick={() => onDelete(task.id)}
          className="rounded-md p-1 text-muted-foreground hover:bg-destructive/10 hover:text-destructive transition-colors"
        >
          <Trash2 className="h-3.5 w-3.5" />
        </button>
      </div>

      <div className="pl-4 pr-8">
        {/* Source */}
        {(task.source_name || task.source_logo) && (
          <div className="mb-2 flex items-center gap-1.5">
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
              <span className="text-[10px] font-medium text-muted-foreground flex items-center gap-1">
                {task.source_name}
                <ExternalLink className="h-2.5 w-2.5" />
              </span>
            )}
          </div>
        )}

        {/* Title */}
        <p
          className={cn(
            "text-sm font-medium leading-snug text-foreground",
            task.status === "completed" && "line-through text-muted-foreground"
          )}
        >
          {task.title}
        </p>

        {/* Description */}
        {task.description && (
          <p className="mt-1 text-xs text-muted-foreground line-clamp-2 leading-relaxed">
            {task.description}
          </p>
        )}

        {/* Footer */}
        <div className="mt-2.5 flex flex-wrap items-center gap-2">
          {/* Priority */}
          {priorityCfg && (
            <span
              className={cn(
                "inline-flex items-center gap-1 text-[10px] font-medium",
                priorityCfg.color
              )}
            >
              <span className={cn("h-1.5 w-1.5 rounded-full", priorityCfg.dot)} />
              {priorityCfg.label}
            </span>
          )}

          {/* Due date */}
          {dueDate && (
            <span
              className={cn(
                "inline-flex items-center gap-1 text-[10px] font-medium",
                isDue
                  ? "text-red-400"
                  : isDueToday
                  ? "text-amber-400"
                  : "text-muted-foreground"
              )}
            >
              {isDue ? (
                <AlertCircle className="h-3 w-3" />
              ) : (
                <Calendar className="h-3 w-3" />
              )}
              {format(dueDate, "MMM d")}
            </span>
          )}

          {/* Reminder */}
          {task.reminder_at && (
            <span className="inline-flex items-center gap-1 text-[10px] text-violet-400 font-medium">
              <Clock className="h-3 w-3" />
              {format(new Date(task.reminder_at), "MMM d, h:mm a")}
            </span>
          )}
        </div>
      </div>
    </div>
  )
}
