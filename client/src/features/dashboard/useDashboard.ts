/**
 * Dashboard data hook (NUMA-113 P4, PLAN 17.3 / 21.2).
 *
 * Single entry point for the home page: reads the shared `useDashboardStore`
 * (PLAN 9 - one source for cross-page dashboard data, no per-render refetch),
 * loads the authenticated profile, and owns the Sync All / Refresh actions.
 */
"use client"

import { useCallback, useEffect, useMemo, useRef, useState } from "react"
import { ApiError } from "@/lib/http"
import { useDashboardStore } from "@/lib/stores"
import { fetchLatestAgentData } from "@/features/agents"
import { fetchCurrentUser } from "./dashboard.api"
import { EMPTY_TASKS, EMPTY_TODAY_TASKS } from "./dashboard.constants"
import type { DashboardUser } from "./dashboard.types"
import { getToken } from "@/lib/session"

/** Minimum spinner time so a cached refresh still reads as an action. */
const REFRESH_MIN_MS = 500
/** Sync is queued server-side; re-poll the aggregate as results land. */
const SYNC_REFRESH_DELAYS_MS = [5000, 15000, 30000]

export function useDashboard() {
  const { stats, statsLoading, fetchStats: loadStats } = useDashboardStore()

  const [user, setUser] = useState<DashboardUser | null>(null)
  const [syncingAll, setSyncingAll] = useState(false)
  const [refreshingStats, setRefreshingStats] = useState(false)

  const syncRefreshTimersRef = useRef<ReturnType<typeof setTimeout>[]>([])

  useEffect(() => {
    if (!getToken()) return

    fetchCurrentUser()
      .then(setUser)
      .catch((err: unknown) => {
        // An auth 401 is already handled: lib/http clears the token and
        // navigates to /auth (NUMA-126). Anything else is not fatal to the
        // page, so the dashboard renders without the user header.
        if (!(err instanceof ApiError)) throw err
      })
  }, [])

  useEffect(() => {
    loadStats()
  }, [loadStats])

  useEffect(() => {
    const timers = syncRefreshTimersRef
    return () => {
      timers.current.forEach((timer) => clearTimeout(timer))
      timers.current = []
    }
  }, [])

  const refreshStatsSilently = useCallback(() => {
    void loadStats(true)
  }, [loadStats])

  const handleRefreshStats = useCallback(async () => {
    if (refreshingStats) return
    const startedAt = Date.now()
    setRefreshingStats(true)
    try {
      await loadStats(true)
    } finally {
      const remaining = Math.max(0, REFRESH_MIN_MS - (Date.now() - startedAt))
      if (remaining > 0) {
        await new Promise((resolve) => setTimeout(resolve, remaining))
      }
      setRefreshingStats(false)
    }
  }, [refreshingStats, loadStats])

  const handleFetchLatest = useCallback(async () => {
    if (syncingAll) return
    setSyncingAll(true)
    syncRefreshTimersRef.current.forEach((timer) => clearTimeout(timer))
    syncRefreshTimersRef.current = []

    try {
      await fetchLatestAgentData({ background: true })
      await loadStats(true)
      syncRefreshTimersRef.current = SYNC_REFRESH_DELAYS_MS.map((delay) =>
        setTimeout(() => {
          void loadStats(true)
        }, delay)
      )
    } catch {
      // Sync is best-effort; the next refresh picks up whatever landed.
    } finally {
      setSyncingAll(false)
    }
  }, [syncingAll, loadStats])

  const upcomingEvents = useMemo(() => {
    if (!stats?.calendar?.upcoming) return []
    const now = new Date()
    return stats.calendar.upcoming.filter((event) => new Date(event.start_at) >= now)
  }, [stats?.calendar?.upcoming])

  const tasks = stats?.tasks || EMPTY_TASKS
  const todayTasks = tasks.today || EMPTY_TODAY_TASKS

  return {
    user,
    stats,
    tasks,
    todayTasks,
    health: stats?.health || {},
    upcomingEvents,
    initialLoading: statsLoading && !stats,
    syncingAll,
    refreshingStats,
    refreshStatsSilently,
    handleRefreshStats,
    handleFetchLatest,
  }
}

export type UseDashboardReturn = ReturnType<typeof useDashboard>
