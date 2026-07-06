import { create } from "zustand"
import type { Task, TaskStats } from "@/features/tasks/tasks.types"
import {
  fetchTasks,
  createTask as apiCreateTask,
  updateTask as apiUpdateTask,
  patchTaskStatus as apiPatchTaskStatus,
  deleteTask as apiDeleteTask,
  fetchStats,
  fetchCompletedHistory,
} from "@/features/tasks/tasks.api"

interface TasksStore {
  // State
  tasks: Task[]
  stats: TaskStats | null
  historyTasks: Task[]
  loadingTasks: boolean
  loadingStats: boolean
  loadingHistory: boolean
  tasksError: string | null
  lastFetchedTasks: number | null
  lastFetchedStats: number | null
  lastFetchedHistory: number | null

  // Actions
  fetchAllTasks: (forceFresh?: boolean) => Promise<void>
  fetchAllStats: (forceFresh?: boolean) => Promise<void>
  fetchAllHistory: (forceFresh?: boolean) => Promise<void>
  createTask: (data: Partial<Task> & { title: string }) => Promise<Task>
  updateTask: (id: string, data: Partial<Task>) => Promise<Task>
  patchTaskStatus: (id: string, status: Task["status"], position?: number) => Promise<Task>
  deleteTask: (id: string) => Promise<void>
  setTasks: (tasks: Task[]) => void
  clearError: () => void
  invalidateStats: () => void
}

// Cache duration: 5 minutes
const CACHE_DURATION = 5 * 60 * 1000
// Stats cache: 30 seconds (changes more frequently)
const STATS_CACHE_DURATION = 30 * 1000
let tasksFetchRequestId = 0

export const useTasksStore = create<TasksStore>((set, get) => ({
  tasks: [],
  stats: null,
  historyTasks: [],
  loadingTasks: false,
  loadingStats: false,
  loadingHistory: false,
  tasksError: null,
  lastFetchedTasks: null,
  lastFetchedStats: null,
  lastFetchedHistory: null,

  fetchAllTasks: async (forceFresh = false) => {
    const { lastFetchedTasks, loadingTasks } = get()
    const now = Date.now()

    if (loadingTasks) return

    if (!forceFresh && lastFetchedTasks && now - lastFetchedTasks < CACHE_DURATION) {
      return
    }

    if (!lastFetchedTasks || forceFresh) {
      set({ loadingTasks: true })
    }

    try {
      set({ tasksError: null })
      const requestId = ++tasksFetchRequestId
      const data = await fetchTasks()
      if (requestId === tasksFetchRequestId) {
        set({ tasks: data, lastFetchedTasks: now })
      }
    } catch (err) {
      set({ tasksError: err instanceof Error ? err.message : "Failed to load tasks" })
    } finally {
      set({ loadingTasks: false })
    }
  },

  fetchAllStats: async (forceFresh = false) => {
    const { lastFetchedStats, loadingStats } = get()
    const now = Date.now()

    if (loadingStats) return

    if (!forceFresh && lastFetchedStats && now - lastFetchedStats < STATS_CACHE_DURATION) {
      return
    }

    if (!lastFetchedStats) {
      set({ loadingStats: true })
    }

    try {
      const data = await fetchStats()
      set({ stats: data, lastFetchedStats: now })
    } catch (err) {
      console.error("Failed to fetch stats:", err)
    } finally {
      set({ loadingStats: false })
    }
  },

  fetchAllHistory: async (forceFresh = false) => {
    const { lastFetchedHistory, loadingHistory } = get()
    const now = Date.now()

    if (loadingHistory) return

    if (!forceFresh && lastFetchedHistory && now - lastFetchedHistory < CACHE_DURATION) {
      return
    }

    if (!lastFetchedHistory) {
      set({ loadingHistory: true })
    }

    try {
      const data = await fetchCompletedHistory()
      set({ historyTasks: data, lastFetchedHistory: now })
    } catch (err) {
      console.error("Failed to fetch history:", err)
    } finally {
      set({ loadingHistory: false })
    }
  },

  createTask: async (data) => {
    const task = await apiCreateTask(data)
    set((state) => ({ tasks: [...state.tasks, task] }))
    // Invalidate stats cache
    set({ lastFetchedStats: null, lastFetchedHistory: null })
    return task
  },

  updateTask: async (id, data) => {
    const { tasks } = get()
    const originalTask = tasks.find((t) => t.id === id)

    // Optimistic update
    set((state) => ({
      tasks: state.tasks.map((t) => (t.id === id ? { ...t, ...data } : t)),
    }))

    try {
      const updated = await apiUpdateTask(id, data)
      set((state) => ({
        tasks: state.tasks.map((t) => (t.id === id ? updated : t)),
      }))
      // Invalidate stats cache if status changed
      if (data.status || data.completed_at !== undefined) {
        set({ lastFetchedStats: null, lastFetchedHistory: null })
      }
      return updated
    } catch (err) {
      // Revert on error
      if (originalTask) {
        set((state) => ({
          tasks: state.tasks.map((t) => (t.id === id ? originalTask : t)),
        }))
      }
      throw err
    }
  },

  patchTaskStatus: async (id, status, position) => {
    const { tasks } = get()
    const originalTask = tasks.find((t) => t.id === id)

    // Optimistic update
    set((state) => ({
      tasks: state.tasks.map((t) =>
        t.id === id ? { ...t, status, ...(position !== undefined && { position }) } : t
      ),
    }))

    try {
      const updated = await apiPatchTaskStatus(id, status, position)
      set((state) => ({
        tasks: state.tasks.map((t) => (t.id === id ? updated : t)),
      }))
      // Invalidate stats cache
      set({ lastFetchedStats: null, lastFetchedHistory: null })
      return updated
    } catch (err) {
      // Revert on error
      if (originalTask) {
        set((state) => ({
          tasks: state.tasks.map((t) => (t.id === id ? originalTask : t)),
        }))
      }
      throw err
    }
  },

  deleteTask: async (id) => {
    const { tasks } = get()
    const deletedTask = tasks.find((t) => t.id === id)

    // Optimistic update
    set((state) => ({
      tasks: state.tasks.filter((t) => t.id !== id),
    }))

    try {
      await apiDeleteTask(id)
      // Invalidate stats cache
      set({ lastFetchedStats: null, lastFetchedHistory: null })
    } catch (err) {
      // Revert on error
      if (deletedTask) {
        set((state) => ({ tasks: [...state.tasks, deletedTask] }))
      }
      throw err
    }
  },

  setTasks: (tasks) => set({ tasks }),

  clearError: () => set({ tasksError: null }),

  invalidateStats: () => set({ lastFetchedStats: null }),
}))
