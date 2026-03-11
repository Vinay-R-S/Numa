"use client"

import React, { useEffect, useState, useCallback } from "react"
import { useRouter } from "next/navigation"
import { CheckSquare, Bell } from "lucide-react"
import { KanbanBoard } from "@/components/tasklist/KanbanBoard"
import { AnalyticsDashboard } from "@/components/tasklist/AnalyticsDashboard"
import { fetchTasks, fetchStats } from "@/components/tasklist/api"
import type { Task, TaskStats } from "@/components/tasklist/types"
import { Skeleton } from "@/components/ui/skeleton"
import { Separator } from "@/components/ui/separator"

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"

export default function TasklistPage() {
  const router = useRouter()
  const [tasks, setTasks] = useState<Task[]>([])
  const [stats, setStats] = useState<TaskStats | null>(null)
  const [loadingTasks, setLoadingTasks] = useState(true)
  const [loadingStats, setLoadingStats] = useState(true)

  // Auth guard
  useEffect(() => {
    const token = localStorage.getItem("numa_token")
    if (!token) {
      router.replace("/auth")
    }
  }, [router])

  const loadTasks = useCallback(async () => {
    setLoadingTasks(true)
    try {
      const data = await fetchTasks()
      setTasks(data)
    } catch (e) {
      console.error(e)
    } finally {
      setLoadingTasks(false)
    }
  }, [])

  const loadStats = useCallback(async () => {
    setLoadingStats(true)
    try {
      const data = await fetchStats()
      setStats(data)
    } catch (e) {
      console.error(e)
    } finally {
      setLoadingStats(false)
    }
  }, [])

  useEffect(() => {
    loadTasks()
    loadStats()
  }, [loadTasks, loadStats])

  // Refresh stats whenever tasks change (debounced)
  const handleTasksChange = useCallback(
    (updated: Task[]) => {
      setTasks(updated)
      // Reload stats after a short debounce
      const t = setTimeout(() => loadStats(), 800)
      return () => clearTimeout(t)
    },
    [loadStats]
  )

  // Web Push reminder scheduler
  useEffect(() => {
    if (!("Notification" in window)) return

    const checkReminders = () => {
      const now = new Date()
      tasks.forEach((task) => {
        if (!task.reminder_at) return
        const reminderTime = new Date(task.reminder_at)
        const diff = reminderTime.getTime() - now.getTime()
        // Fire if within the next minute
        if (diff > 0 && diff <= 60_000) {
          setTimeout(() => {
            if (Notification.permission === "granted") {
              new Notification(`⏰ Reminder: ${task.title}`, {
                body: task.description ?? "Task reminder from NUMA",
                icon: task.source_logo ?? undefined,
              })
            }
          }, diff)
        }
      })
    }

    if (Notification.permission === "default") {
      Notification.requestPermission().then((perm) => {
        if (perm === "granted") checkReminders()
      })
    } else if (Notification.permission === "granted") {
      checkReminders()
    }
  }, [tasks])

  return (
    <div className="min-h-full px-6 py-6 space-y-10 max-w-400 mx-auto">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary/10 ring-1 ring-primary/20">
            <CheckSquare className="h-5 w-5 text-primary" />
          </div>
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-foreground">Task List</h1>
            <p className="text-sm text-muted-foreground">
              Manage your work across all stages
            </p>
          </div>
        </div>
        <button
          title="Enable notifications"
          onClick={() => Notification.requestPermission()}
          className="flex items-center gap-2 rounded-lg border border-border/50 px-3 py-2 text-sm text-muted-foreground hover:bg-accent hover:text-foreground transition-colors"
        >
          <Bell className="h-4 w-4" />
          <span className="hidden sm:inline">Notifications</span>
        </button>
      </div>

      {/* ── Kanban Board ─────────────────────────────────────────────────────── */}
      {loadingTasks ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {[...Array(4)].map((_, i) => (
            <Skeleton key={i} className="h-96 rounded-2xl" />
          ))}
        </div>
      ) : (
        <KanbanBoard
          tasks={tasks}
          onTasksChange={handleTasksChange}
          onRefresh={() => { loadTasks(); loadStats() }}
        />
      )}

      <Separator className="opacity-20" />

      {/* ── Analytics Dashboard ───────────────────────────────────────────────── */}
      <AnalyticsDashboard stats={stats} loading={loadingStats} />

      {/* Bottom spacing */}
      <div className="h-8" />
    </div>
  )
}
