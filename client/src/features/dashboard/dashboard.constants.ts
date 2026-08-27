/**
 * Dashboard presentation constants (NUMA-113 P4, PLAN 17.3).
 */
import type { DashboardTasks, DashboardTodayTasks } from "./dashboard.types"

export const ICON_COLORS = {
  tasks: "text-blue-400",
  completed: "text-emerald-400",
  inprogress: "text-amber-400",
  pending: "text-rose-400",
  streak: "text-orange-400",
  calendar: "text-sky-400",
  slack: "text-purple-400",
  journal: "text-pink-400",
  health: "text-emerald-400",
  steps: "text-cyan-400",
  calories: "text-orange-400",
  sleep: "text-indigo-400",
  distance: "text-violet-400",
  github: "text-violet-400",
  active: "text-emerald-400",
  heartRate: "text-rose-400",
  heartPoints: "text-pink-400",
} as const

/** Stable keys for the first-load stat card placeholders (no array-index keys). */
export const STAT_SKELETON_KEYS = ["stat-1", "stat-2", "stat-3", "stat-4", "stat-5"]

/** Rendered while stats are absent; kept module-level so it is referentially stable. */
export const EMPTY_TASKS: DashboardTasks = {
  total: 0,
  completed: 0,
  inprogress: 0,
  pending: 0,
  streak: 0,
  recent: [],
}

export const EMPTY_TODAY_TASKS: DashboardTodayTasks = {
  total: 0,
  completed: 0,
  inprogress: 0,
  pending: 0,
}
