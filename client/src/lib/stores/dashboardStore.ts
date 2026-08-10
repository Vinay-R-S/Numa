import { create } from "zustand"
import { fetchDashboardStats } from "@/features/dashboard/dashboard.api"
import type { DashboardStats } from "@/features/dashboard/dashboard.types"

interface DashboardStore {
  stats: DashboardStats | null
  statsLoading: boolean
  error: string | null
  lastFetched: number | null

  fetchStats: (force?: boolean) => Promise<void>
  invalidate: () => void
  clearError: () => void
}

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
      const data = await fetchDashboardStats()
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
