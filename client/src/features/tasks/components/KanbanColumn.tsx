"use client"

import React from "react"
import { useDroppable } from "@dnd-kit/core"
import { SortableContext, verticalListSortingStrategy } from "@dnd-kit/sortable"
import { Plus } from "lucide-react"
import type { Task, TaskStatus } from "../tasks.types"
import { COLUMN_CONFIG } from "../tasks.types"
import { TaskCard } from "./TaskCard"
import { ScrollArea } from "@/components/ui/scroll-area"
import { cn } from "@/lib/utils"

const MAX_VISIBLE_TASK_CARDS = 4
const ESTIMATED_TASK_CARD_HEIGHT = 112
const TASK_CARD_GAP = 10
const TASK_LIST_VERTICAL_PADDING = 24

interface KanbanColumnProps {
  status: TaskStatus
  tasks: Task[]
  onAddTask: (status: TaskStatus) => void
  onEditTask: (task: Task) => void
  onDeleteTask: (id: string) => void
  onViewTask: (task: Task) => void
}

export function KanbanColumn({
  status,
  tasks,
  onAddTask,
  onEditTask,
  onDeleteTask,
  onViewTask,
}: KanbanColumnProps) {
  const { setNodeRef, isOver } = useDroppable({ id: status })
  const config = COLUMN_CONFIG[status]
  const visibleCards = MAX_VISIBLE_TASK_CARDS
  const scrollAreaHeight =
    visibleCards * ESTIMATED_TASK_CARD_HEIGHT +
    (visibleCards - 1) * TASK_CARD_GAP +
    TASK_LIST_VERTICAL_PADDING

  return (
    <div
      className={cn(
        "flex self-start flex-col rounded-2xl border transition-all duration-200",
        config.bgColor,
        config.borderColor,
        isOver && "ring-2 ring-offset-2 ring-offset-background",
        isOver && status === "planned" && "ring-blue-500/50",
        isOver && status === "inprogress" && "ring-amber-500/50",
        isOver && status === "completed" && "ring-emerald-500/50",
        isOver && status === "pending" && "ring-rose-500/50",
      )}
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
      <ScrollArea className="p-3" style={{ height: scrollAreaHeight }}>
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
                onView={onViewTask}
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
