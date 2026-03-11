"use client"

import React from "react"
import { useDroppable } from "@dnd-kit/core"
import { SortableContext, verticalListSortingStrategy } from "@dnd-kit/sortable"
import { Plus } from "lucide-react"
import type { Task, TaskStatus } from "./types"
import { COLUMN_CONFIG } from "./types"
import { TaskCard } from "./TaskCard"
import { ScrollArea } from "@/components/ui/scroll-area"
import { cn } from "@/lib/utils"

interface KanbanColumnProps {
  status: TaskStatus
  tasks: Task[]
  onAddTask: (status: TaskStatus) => void
  onEditTask: (task: Task) => void
  onDeleteTask: (id: string) => void
}

export function KanbanColumn({
  status,
  tasks,
  onAddTask,
  onEditTask,
  onDeleteTask,
}: KanbanColumnProps) {
  const { setNodeRef, isOver } = useDroppable({ id: status })
  const config = COLUMN_CONFIG[status]

  return (
    <div
      className={cn(
        "flex flex-col rounded-2xl border transition-all duration-200",
        config.bgColor,
        config.borderColor,
        isOver && "ring-2 ring-offset-2 ring-offset-background",
        isOver && status === "planned" && "ring-blue-500/50",
        isOver && status === "inprogress" && "ring-amber-500/50",
        isOver && status === "completed" && "ring-emerald-500/50",
        isOver && status === "pending" && "ring-rose-500/50",
      )}
      style={{ minHeight: 400 }}
    >
      {/* Column Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-white/5">
        <div className="flex items-center gap-2">
          <span className={cn("h-2 w-2 rounded-full", {
            "bg-blue-400": status === "planned",
            "bg-amber-400": status === "inprogress",
            "bg-emerald-400": status === "completed",
            "bg-rose-400": status === "pending",
          })} />
          <h3 className={cn("text-sm font-semibold", config.color)}>
            {config.label}
          </h3>
          <span className="rounded-full bg-white/10 px-2 py-0.5 text-xs font-medium text-muted-foreground">
            {tasks.length}
          </span>
        </div>
        <button
          onClick={() => onAddTask(status)}
          className="rounded-lg p-1 text-muted-foreground hover:bg-white/10 hover:text-foreground transition-colors"
        >
          <Plus className="h-4 w-4" />
        </button>
      </div>

      {/* Tasks */}
      <ScrollArea className="flex-1 p-3">
        <SortableContext
          id={status}
          items={tasks.map((t) => t.id)}
          strategy={verticalListSortingStrategy}
        >
          <div ref={setNodeRef} className="flex flex-col gap-2.5 min-h-25">
            {tasks.map((task) => (
              <TaskCard
                key={task.id}
                task={task}
                onEdit={onEditTask}
                onDelete={onDeleteTask}
              />
            ))}
            {tasks.length === 0 && (
              <div className="flex h-20 items-center justify-center rounded-xl border border-dashed border-white/10 text-xs text-muted-foreground">
                Drop tasks here
              </div>
            )}
          </div>
        </SortableContext>
      </ScrollArea>
    </div>
  )
}
