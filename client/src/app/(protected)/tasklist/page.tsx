"use client"

import React, { useEffect, useState, useCallback, useRef } from "react"
import { CheckSquare, Bell, ChevronDown, ChevronRight, History, RefreshCw } from "lucide-react"
import { KanbanBoard } from "@/components/tasklist/KanbanBoard"
import { AnalyticsDashboard } from "@/components/tasklist/AnalyticsDashboard"
import { TaskDetailSheet } from "@/components/tasklist/TaskDetailSheet"
import { HeaderActionButton } from "@/components/ui/header-action-button"
import { useTasksStore } from "@/lib/stores"
import { fetchLatestAgentData } from "@/components/agents/masterAgentApi"
import type { Task } from "@/components/tasklist/types"
import { PRIORITY_CONFIG } from "@/components/tasklist/types"
import { Skeleton } from "@/components/ui/skeleton"
import { Separator } from "@/components/ui/separator"
import { format } from "date-fns"
import { cn } from "@/lib/utils"

export default function TasklistPage() {
  // Use global store for cached data
  const {
    tasks,
    stats,
    historyTasks,
    loadingTasks,
    loadingStats,
    loadingHistory,
    tasksError,
    fetchAllTasks,
    fetchAllStats,
    fetchAllHistory,
    setTasks,
    invalidateStats,
  } = useTasksStore()

  // Stable ref for debouncing the stats refresh triggered by task changes
  const statsTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  // History (completed tasks from previous days)
  const [historyExpanded, setHistoryExpanded] = useState(false)
  const [syncingAll, setSyncingAll] = useState(false)
  const [notificationPermission, setNotificationPermission] =
    useState<NotificationPermission | null>(null)

  // Detail sheet for history tasks
  const [historyDetailTask, setHistoryDetailTask] = useState<Task | null>(null)
  const [historyDetailOpen, setHistoryDetailOpen] = useState(false)

  // Fetch all data on mount (will use cache if available)
  useEffect(() => {
    fetchAllTasks()
    fetchAllStats()
    fetchAllHistory()
  }, [fetchAllTasks, fetchAllStats, fetchAllHistory])

  useEffect(() => {
    if (typeof window === "undefined" || !("Notification" in window)) return
    const timeoutId = window.setTimeout(() => {
      setNotificationPermission(Notification.permission)
    }, 0)

    return () => window.clearTimeout(timeoutId)
  }, [])

  // Clean up stats debounce timer on unmount
  useEffect(() => () => {
    if (statsTimerRef.current) clearTimeout(statsTimerRef.current)
  }, [])

  // Refresh stats whenever tasks change (debounced)
  const handleTasksChange = useCallback(
    (updated: Task[]) => {
      setTasks(updated)
      if (statsTimerRef.current) clearTimeout(statsTimerRef.current)
      statsTimerRef.current = setTimeout(() => {
        invalidateStats()
        fetchAllStats(true)
      }, 800)
    },
    [setTasks, invalidateStats, fetchAllStats]
  )

  // Handle manual refresh
  const handleRefresh = useCallback(async () => {
    await Promise.all([fetchAllTasks(true), fetchAllStats(true), fetchAllHistory(true)])
  }, [fetchAllTasks, fetchAllStats, fetchAllHistory])

  const handleSyncAll = useCallback(async () => {
    if (syncingAll) return

    setSyncingAll(true)
    try {
      await fetchLatestAgentData()
      await handleRefresh()
    } finally {
      setSyncingAll(false)
    }
  }, [handleRefresh, syncingAll])

  // Web Push reminder scheduler - only prompt once, persist choice
  useEffect(() => {
    if (!("Notification" in window)) return

    const checkReminders = () => {
      const now = new Date()
      tasks.forEach((task) => {
        if (!task.reminder_at) return
        const reminderTime = new Date(task.reminder_at)
        const diff = reminderTime.getTime() - now.getTime()
        if (diff > 0 && diff <= 60_000) {
          setTimeout(() => {
            if (Notification.permission === "granted") {
              new Notification(`Reminder: ${task.title}`, {
                body: task.description ?? "Task reminder from NUMA",
                icon: task.source_logo ?? undefined,
              })
            }
          }, diff)
        }
      })
    }

    if (Notification.permission === "granted") {
      checkReminders()
    }
  }, [tasks])

  return (
    <div className="min-h-full px-3 py-4 space-y-6 max-w-[1600px] mx-auto sm:px-6 sm:py-6 sm:space-y-10">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-primary/10 ring-1 ring-primary/20 sm:h-10 sm:w-10">
            <CheckSquare className="h-4 w-4 text-primary sm:h-5 sm:w-5" />
          </div>
          <div className="min-w-0">
            <h1 className="text-xl font-bold tracking-tight text-foreground sm:text-2xl">Task List</h1>
            <p className="hidden text-sm text-muted-foreground sm:block">
              Manage your work across all stages
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <HeaderActionButton
            icon={RefreshCw}
            label="Sync"
            loading={syncingAll}
            title={syncingAll ? "Syncing all task sources" : "Sync all task sources"}
            onClick={() => void handleSyncAll()}
            disabled={syncingAll}
          >
            {syncingAll ? "Syncing..." : "Sync"}
          </HeaderActionButton>
          <HeaderActionButton
            icon={RefreshCw}
            label="Refresh"
            loading={loadingTasks}
            title={loadingTasks ? "Refreshing tasks" : "Refresh tasks"}
            onClick={() => void handleRefresh()}
            disabled={loadingTasks}
          />
          {notificationPermission !== null && notificationPermission !== "granted" && (
            <HeaderActionButton
              icon={Bell}
              label="Enable Notifications"
              title="Enable notifications for task reminders"
              onClick={() => {
                void Notification.requestPermission().then(setNotificationPermission)
              }}
            />
          )}
        </div>
      </div>

      {/* ── Kanban Board ─────────────────────────────────────────────────────── */}
      {loadingTasks && tasks.length === 0 ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {[...Array(4)].map((_, i) => (
            <Skeleton key={i} className="h-96 rounded-2xl" />
          ))}
        </div>
      ) : (
        <div className="space-y-4">
          {tasksError && (
            <div className="rounded-xl border border-destructive/50 bg-destructive/10 px-4 py-3 text-sm text-destructive">
              <p>{tasksError}</p>
            </div>
          )}

          <KanbanBoard
            tasks={tasks}
            onTasksChange={handleTasksChange}
          />
        </div>
      )}

      <Separator className="opacity-20" />

      {/* ── Completed History ─────────────────────────────────────────────────── */}
      <div>
        <button
          onClick={() => setHistoryExpanded((v) => !v)}
          className="flex w-full items-center gap-3 text-left group"
        >
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-emerald-500/10 sm:h-9 sm:w-9">
            <History className="h-4 w-4 text-emerald-400 sm:h-5 sm:w-5" />
          </div>
          <div className="flex-1 min-w-0">
            <h2 className="text-lg font-bold text-foreground sm:text-xl">Completed History</h2>
            <p className="text-sm text-muted-foreground">
              Tasks completed on previous days
              {!loadingHistory && historyTasks.length > 0 && (
                <span className="ml-1 text-emerald-400 font-medium">
                  · {historyTasks.length} task{historyTasks.length !== 1 ? "s" : ""}
                </span>
              )}
            </p>
          </div>
          <div className="text-muted-foreground group-hover:text-foreground transition-colors">
            {historyExpanded ? (
              <ChevronDown className="h-5 w-5" />
            ) : (
              <ChevronRight className="h-5 w-5" />
            )}
          </div>
        </button>

        {historyExpanded && (
          <div className="mt-4">
            {loadingHistory && historyTasks.length === 0 ? (
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
                {[...Array(6)].map((_, i) => (
                  <Skeleton key={i} className="h-20 rounded-xl" />
                ))}
              </div>
            ) : historyTasks.length === 0 ? (
              <div className="flex h-24 items-center justify-center rounded-2xl border border-dashed border-white/10 text-sm text-muted-foreground">
                No completed tasks from previous days
              </div>
            ) : (
              <div className="grid grid-cols-1 gap-2.5 sm:grid-cols-2 lg:grid-cols-3">
                {historyTasks.map((task) => {
                  const priorityCfg = task.priority ? PRIORITY_CONFIG[task.priority] : null
                  return (
                    <button
                      key={task.id}
                      onClick={() => {
                        setHistoryDetailTask(task)
                        setHistoryDetailOpen(true)
                      }}
                      className="group text-left rounded-xl border border-border/50 bg-card p-3 hover:border-border hover:shadow-md transition-all duration-200"
                    >
                      <p className="text-sm font-medium text-muted-foreground line-through line-clamp-1 group-hover:text-foreground transition-colors">
                        {task.title}
                      </p>
                      <div className="mt-1.5 flex items-center gap-2 flex-wrap">
                        {task.completed_at && (
                          <span className="text-[10px] text-emerald-500/80 font-medium">
                            ✓ {format(new Date(task.completed_at), "MMM d, yyyy")}
                          </span>
                        )}
                        {priorityCfg && (
                          <span className={cn("text-[10px] font-medium", priorityCfg.color)}>
                            <span className={cn("inline-block h-1.5 w-1.5 rounded-full mr-1 align-middle", priorityCfg.dot)} />
                            {priorityCfg.label}
                          </span>
                        )}
                      </div>
                    </button>
                  )
                })}
              </div>
            )}
          </div>
        )}
      </div>

      <Separator className="opacity-20" />

      {/* ── Analytics Dashboard ───────────────────────────────────────────────── */}
      <AnalyticsDashboard stats={stats} loading={loadingStats && !stats} />

      {/* Bottom spacing */}
      <div className="h-8" />

      {/* History task detail sheet */}
      <TaskDetailSheet
        task={historyDetailTask}
        open={historyDetailOpen}
        onClose={() => setHistoryDetailOpen(false)}
      />
    </div>
  )
}
