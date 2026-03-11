"use client"

import React, { useState, useCallback, useEffect } from "react"
import {
  DndContext,
  DragOverlay,
  PointerSensor,
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

  useEffect(() => {
    tasks.forEach((t) => {
      if (t.reminder_at) scheduleReminder(t.id, t.title, t.reminder_at)
    })
  }, [tasks])
  const [dialogOpen, setDialogOpen] = useState(false)
  const [editingTask, setEditingTask] = useState<Task | null>(null)
  const [dialogDefaultStatus, setDialogDefaultStatus] = useState<TaskStatus>("planned")

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 5 } })
  )

  const tasksByStatus = useCallback(
    (status: TaskStatus) =>
      tasks
        .filter((t) => t.status === status)
        .sort((a, b) => a.position - b.position),
    [tasks]
  )

  function handleDragStart(event: DragStartEvent) {
    const task = tasks.find((t) => t.id === event.active.id)
    if (task) setActiveTask(task)
  }

  function handleDragOver(event: DragOverEvent) {
    const { active, over } = event
    if (!over) return

    const activeTask = tasks.find((t) => t.id === active.id)
    if (!activeTask) return

    // over could be a column id or a task id
    const overStatus = STATUSES.includes(over.id as TaskStatus)
      ? (over.id as TaskStatus)
      : tasks.find((t) => t.id === over.id)?.status

    if (!overStatus || activeTask.status === overStatus) return

    // Optimistically move the card to the new column
    onTasksChange(
      tasks.map((t) =>
        t.id === activeTask.id ? { ...t, status: overStatus } : t
      )
    )
  }

  async function handleDragEnd(event: DragEndEvent) {
    const { active, over } = event
    setActiveTask(null)
    if (!over) return

    const draggedTask = tasks.find((t) => t.id === active.id)
    if (!draggedTask) return

    const overStatus = STATUSES.includes(over.id as TaskStatus)
      ? (over.id as TaskStatus)
      : tasks.find((t) => t.id === over.id)?.status

    if (!overStatus) return

    const newStatus = overStatus
    const columnTasks = tasks
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
      onTasksChange(
        tasks.map((t) =>
          t.id === updated.id ? updated : t
        )
      )
    } catch {
      // Revert on error
      onRefresh()
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
    onTasksChange(tasks.filter((t) => t.id !== id))
    try {
      await deleteTask(id)
    } catch {
      onRefresh()
      toast.error("Failed to delete task")
    }
  }

  async function handleSaveTask(data: Partial<Task> & { title: string }): Promise<Task> {
    if (editingTask) {
      const updated = await updateTask(editingTask.id, data)
      onTasksChange(tasks.map((t) => (t.id === updated.id ? updated : t)))
      return updated
    } else {
      const created = await createTask({ ...data, status: data.status ?? dialogDefaultStatus })
      onTasksChange([...tasks, created])
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
    </div>
  )
}
