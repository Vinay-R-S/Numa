"use client"

import React, { useState, useCallback, useEffect } from "react"
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
import { arrayMove } from "@dnd-kit/sortable"
import { Plus, RefreshCw } from "lucide-react"
import type { Task, TaskStatus } from "./types"
import { KanbanColumn } from "./KanbanColumn"
import { TaskCard } from "./TaskCard"
import { TaskDialog } from "./TaskDialog"
import { TaskDetailSheet } from "./TaskDetailSheet"
import { patchTaskStatus, createTask, updateTask, deleteTask } from "./api"
import { Button } from "@/components/ui/button"
import { toast } from "./toast"
import { scheduleReminder, cancelReminder } from "./notifications"

const STATUSES: TaskStatus[] = ["planned", "inprogress", "completed", "pending"]

interface KanbanBoardProps {
  tasks: Task[]
  onTasksChange: (tasks: Task[]) => void
  onRefresh: () => void
}

export function KanbanBoard({ tasks, onTasksChange, onRefresh }: KanbanBoardProps) {
  const [activeTask, setActiveTask] = useState<Task | null>(null)
  // Local copy for optimistic drag/edit updates — parent is notified only after confirmed API responses
  const [localTasks, setLocalTasks] = useState(tasks)

  // Keep local state in sync whenever the parent pushes a confirmed update or refreshes
  useEffect(() => {
    setLocalTasks(tasks)
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

  const tasksByStatus = useCallback(
    (status: TaskStatus) =>
      localTasks
        .filter((t) => t.status === status)
        .sort((a, b) => a.position - b.position),
    [localTasks]
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

    // Update local state only — parent is NOT notified during hover, avoiding spurious stat refreshes
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
    const columnTasks = snapshot
      .filter((t) => t.status === newStatus)
      .sort((a, b) => a.position - b.position)

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
      // Revert local UI to last confirmed server state — no full skeleton reload
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
    cancelReminder(id)
    const optimistic = localTasks.filter((t) => t.id !== id)
    setLocalTasks(optimistic)
    try {
      await deleteTask(id)
      onTasksChange(optimistic)
    } catch {
      setLocalTasks(tasks) // revert local UI
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
            {tasks.length} total task{tasks.length !== 1 ? "s" : ""}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="ghost" size="icon" onClick={onRefresh} className="text-muted-foreground">
            <RefreshCw className="h-4 w-4" />
          </Button>
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
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
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
