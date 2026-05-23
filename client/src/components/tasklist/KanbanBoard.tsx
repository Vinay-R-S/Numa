"use client"

import React, { useState, useCallback, useEffect, useRef } from "react"
import {
  DndContext,
  DragOverlay,
  MouseSensor,
  TouchSensor,
  useSensor,
  useSensors,
  closestCorners,
  type DragStartEvent,
  type DragEndEvent,
  type DragOverEvent,
} from "@dnd-kit/core"
import { Plus } from "lucide-react"
import type { Task, TaskStatus } from "./types"
import { KanbanColumn } from "./KanbanColumn"
import { TaskCard } from "./TaskCard"
import { TaskDialog } from "./TaskDialog"
import { TaskDetailSheet } from "./TaskDetailSheet"
import { patchTaskStatus, createTask, updateTask, deleteTask } from "./api"
import { Button } from "@/components/ui/button"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { toast } from "./toast"
import { scheduleReminder, cancelReminder } from "./notifications"

const STATUSES: TaskStatus[] = ["planned", "inprogress", "completed", "pending"]

type TaskSortMode = "position" | "due-date" | "priority"

const PRIORITY_SORT_WEIGHT: Record<"low" | "medium" | "high" | "urgent", number> = {
  low: 1,
  medium: 2,
  high: 3,
  urgent: 4,
}

function dueDateSortValue(task: Task): number {
  if (!task.due_date) {
    return Number.POSITIVE_INFINITY
  }

  const parsed = new Date(task.due_date).getTime()
  return Number.isNaN(parsed) ? Number.POSITIVE_INFINITY : parsed
}

function prioritySortValue(task: Task): number {
  if (!task.priority) {
    return 0
  }

  return PRIORITY_SORT_WEIGHT[task.priority]
}

interface KanbanBoardProps {
  tasks: Task[]
  onTasksChange: (tasks: Task[]) => void
}

export function KanbanBoard({ tasks, onTasksChange }: KanbanBoardProps) {
  const [activeTask, setActiveTask] = useState<Task | null>(null)
  // Local copy for optimistic drag/edit updates - parent is notified only after confirmed API responses
  const [localTasks, setLocalTasks] = useState(tasks)
  const deletedTaskIdsRef = useRef<Set<string>>(new Set())
  const [sortMode, setSortMode] = useState<TaskSortMode>("position")

  // Keep local state in sync whenever the parent pushes a confirmed update or refreshes
  useEffect(() => {
    setLocalTasks(tasks.filter((task) => !deletedTaskIdsRef.current.has(task.id)))
  }, [tasks])

  useEffect(() => {
    tasks.forEach((t) => {
      if (t.reminder_at) scheduleReminder(t.id, t.title, t.reminder_at)
    })
  }, [tasks])
  const [dialogOpen, setDialogOpen] = useState(false)
  const [editingTask, setEditingTask] = useState<Task | null>(null)
  const [dialogDefaultStatus, setDialogDefaultStatus] = useState<TaskStatus>("planned")

  // Detail (read-only) sheet
  const [detailTask, setDetailTask] = useState<Task | null>(null)
  const [detailOpen, setDetailOpen] = useState(false)

  function handleViewTask(task: Task) {
    setDetailTask(task)
    setDetailOpen(true)
  }

  const sensors = useSensors(
    useSensor(MouseSensor, { activationConstraint: { distance: 5 } }),
    // Hold for 250 ms on touch before activating drag so scroll still works normally
    useSensor(TouchSensor, { activationConstraint: { delay: 250, tolerance: 5 } })
  )

  const sortedTasks = useCallback(
    (items: Task[]) => {
      return [...items].sort((a, b) => {
        if (sortMode === "due-date") {
          const dueDiff = dueDateSortValue(a) - dueDateSortValue(b)
          if (dueDiff !== 0) {
            return dueDiff
          }

          const priorityDiff = prioritySortValue(b) - prioritySortValue(a)
          if (priorityDiff !== 0) {
            return priorityDiff
          }
        }

        if (sortMode === "priority") {
          const priorityDiff = prioritySortValue(b) - prioritySortValue(a)
          if (priorityDiff !== 0) {
            return priorityDiff
          }

          const dueDiff = dueDateSortValue(a) - dueDateSortValue(b)
          if (dueDiff !== 0) {
            return dueDiff
          }
        }

        return a.position - b.position
      })
    },
    [sortMode]
  )

  const tasksByStatus = useCallback(
    (status: TaskStatus) =>
      sortedTasks(localTasks.filter((t) => t.status === status)),
    [localTasks, sortedTasks]
  )

  function handleDragStart(event: DragStartEvent) {
    const task = localTasks.find((t) => t.id === event.active.id)
    if (task) setActiveTask(task)
  }

  function handleDragOver(event: DragOverEvent) {
    const { active, over } = event
    if (!over) return

    const dragging = localTasks.find((t) => t.id === active.id)
    if (!dragging) return

    // over could be a column id or a task id
    const overStatus = STATUSES.includes(over.id as TaskStatus)
      ? (over.id as TaskStatus)
      : localTasks.find((t) => t.id === over.id)?.status

    if (!overStatus || dragging.status === overStatus) return

    // Update local state only - parent is NOT notified during hover, avoiding spurious stat refreshes
    setLocalTasks((prev) =>
      prev.map((t) => (t.id === dragging.id ? { ...t, status: overStatus } : t))
    )
  }

  async function handleDragEnd(event: DragEndEvent) {
    const { active, over } = event
    setActiveTask(null)
    if (!over) return

    // Use localTasks so the optimistic column move from handleDragOver is already reflected
    const snapshot = localTasks
    const draggedTask = snapshot.find((t) => t.id === active.id)
    if (!draggedTask) return

    const overStatus = STATUSES.includes(over.id as TaskStatus)
      ? (over.id as TaskStatus)
      : snapshot.find((t) => t.id === over.id)?.status

    if (!overStatus) return

    const newStatus = overStatus
    const columnTasks = sortedTasks(snapshot.filter((t) => t.status === newStatus))

    // Determine new position
    let newIndex = columnTasks.length
    if (!STATUSES.includes(over.id as TaskStatus)) {
      const overIdx = columnTasks.findIndex((t) => t.id === over.id)
      if (overIdx !== -1) newIndex = overIdx
    }

    try {
      const updated = await patchTaskStatus(draggedTask.id, newStatus, newIndex)
      const confirmed = snapshot.map((t) => (t.id === updated.id ? updated : t))
      setLocalTasks(confirmed)
      onTasksChange(confirmed)
    } catch {
      // Revert local UI to last confirmed server state - no full skeleton reload
      setLocalTasks(tasks)
      toast.error("Failed to move task")
    }
  }

  function handleAddTask(status: TaskStatus) {
    setEditingTask(null)
    setDialogDefaultStatus(status)
    setDialogOpen(true)
  }

  function handleEditTask(task: Task) {
    setEditingTask(task)
    setDialogOpen(true)
  }

  async function handleDeleteTask(id: string) {
    if (!confirm("Delete this task?")) return
    const previous = localTasks
    const deletedTask = localTasks.find((task) => task.id === id)
    cancelReminder(id)
    deletedTaskIdsRef.current.add(id)
    const optimistic = localTasks.filter((t) => t.id !== id)
    setLocalTasks(optimistic)
    onTasksChange(optimistic)
    try {
      await deleteTask(id)
    } catch {
      deletedTaskIdsRef.current.delete(id)
      if (deletedTask) {
        const restored = previous.some((task) => task.id === deletedTask.id)
          ? previous
          : [...previous, deletedTask]
        setLocalTasks(restored)
        onTasksChange(restored)
      }
      toast.error("Failed to delete task")
    }
  }

  async function handleSaveTask(data: Partial<Task> & { title: string }): Promise<Task> {
    if (editingTask) {
      const updated = await updateTask(editingTask.id, data)
      const merged = localTasks.map((t) => (t.id === updated.id ? updated : t))
      setLocalTasks(merged)
      onTasksChange(merged)
      return updated
    } else {
      const created = await createTask({ ...data, status: data.status ?? dialogDefaultStatus })
      const merged = [...localTasks, created]
      setLocalTasks(merged)
      onTasksChange(merged)
      return created
    }
  }

  return (
    <div>
      {/* Board Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-xl font-bold text-foreground">Task Board</h2>
          <p className="text-sm text-muted-foreground mt-0.5">
            {localTasks.length} total task{localTasks.length !== 1 ? "s" : ""}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-48">
            <Select
              value={sortMode}
              onValueChange={(value) => {
                if (value === "position" || value === "due-date" || value === "priority") {
                  setSortMode(value)
                }
              }}
            >
              <SelectTrigger className="h-9">
                <SelectValue placeholder="Sort tasks" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="position">Sort: Manual</SelectItem>
                <SelectItem value="due-date">Sort: Earliest Due Date</SelectItem>
                <SelectItem value="priority">Sort: Priority</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <Button
            size="sm"
            onClick={() => handleAddTask("planned")}
            className="gap-2"
          >
            <Plus className="h-4 w-4" />
            New Task
          </Button>
        </div>
      </div>

      {/* Kanban Grid */}
      <DndContext
        sensors={sensors}
        collisionDetection={closestCorners}
        onDragStart={handleDragStart}
        onDragOver={handleDragOver}
        onDragEnd={handleDragEnd}
      >
        <div className="grid grid-cols-1 items-start gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {STATUSES.map((status) => (
            <KanbanColumn
              key={status}
              status={status}
              tasks={tasksByStatus(status)}
              onAddTask={handleAddTask}
              onEditTask={handleEditTask}
              onDeleteTask={handleDeleteTask}
              onViewTask={handleViewTask}
            />
          ))}
        </div>

        <DragOverlay>
          {activeTask && (
            <TaskCard
              task={activeTask}
              onEdit={() => {}}
              onDelete={() => {}}
              overlay
            />
          )}
        </DragOverlay>
      </DndContext>

      {/* Task Dialog */}
      <TaskDialog
        open={dialogOpen}
        onClose={() => setDialogOpen(false)}
        onSave={handleSaveTask}
        task={editingTask}
        defaultStatus={dialogDefaultStatus}
      />

      {/* Task Detail Sheet */}
      <TaskDetailSheet
        task={detailTask}
        open={detailOpen}
        onClose={() => setDetailOpen(false)}
        onEdit={(task) => {
          setDetailOpen(false)
          handleEditTask(task)
        }}
      />
    </div>
  )
}
