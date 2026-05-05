import { create } from "zustand"

interface DashboardStats {
  tasks: {
    total: number
    completed: number
    inprogress: number
    pending: number
    streak: number
    recent: Array<{
      title: string
      status: string
      priority?: string
      source_name?: string
    }>
  }
  calendar: {
    today_events: number
    upcoming: Array<{ title: string; start_at: string; end_at: string }>
  }
  slack: { messages_7d: number; active_channels: number }
  health: {
    steps?: number
    active_minutes?: number
    calories?: number
    sleep_hours?: number
    distance_km?: number
  }
  github: { connected: boolean; username?: string | null }
  journal: { has_today: boolean; today_mood?: string | null; streak: number }
}

interface DashboardStore {
  stats: DashboardStats | null
  statsLoading: boolean
  error: string | null
  lastFetched: number | null

  fetchStats: (force?: boolean) => Promise<void>
  invalidate: () => void
  clearError: () => void
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

const STALE_THRESHOLD = 60 * 1000

export const useDashboardStore = create<DashboardStore>((set, get) => ({
  stats: null,
  statsLoading: false,
  error: null,
  lastFetched: null,

  fetchStats: async (force = false) => {
    const { lastFetched, statsLoading, stats } = get()
    const now = Date.now()

    if (statsLoading) return

    const isStale = !lastFetched || now - lastFetched >= STALE_THRESHOLD

    if (!force && !isStale) return

    // Only show loading skeleton on the very first fetch (no cached data yet)
    if (!stats) {
      set({ statsLoading: true })
    }

    try {
      set({ error: null })
      const token =
        typeof window !== "undefined"
          ? localStorage.getItem("numa_token")
          : null
      const res = await fetch(`${API_BASE}/api/dashboard/stats`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data: DashboardStats = await res.json()
      set({ stats: data, lastFetched: Date.now() })
    } catch (err) {
      const msg =
        err instanceof Error ? err.message : "Failed to load dashboard stats"
      set({ error: msg })
    } finally {
      set({ statsLoading: false })
    }
  },

  invalidate: () => set({ lastFetched: null }),

  clearError: () => set({ error: null }),
}))

export type { DashboardStats }
