/**
 * Dashboard domain types (NUMA-113 P4, PLAN 5.3 / 21.2).
 *
 * Mirrors the aggregated payload of `GET /api/dashboard/stats`
 * (`server/src/dashboard/router.py`). Moved here from `lib/stores/dashboardStore.ts`
 * so the store, the API module and the components share one contract.
 * Date/timestamp fields stay plain strings: the backend serializes
 * `date`/`datetime` with `isoformat()`.
 */

export interface DashboardRecentTask {
  title: string
  status: string
  priority?: string | null
  due_date?: string | null
  source_name?: string | null
  created_at?: string | null
}

export interface DashboardTodayTasks {
  total: number
  completed: number
  inprogress: number
  pending: number
}

export interface DashboardTasks {
  total: number
  completed: number
  inprogress: number
  pending: number
  today?: DashboardTodayTasks
  streak: number
  recent: DashboardRecentTask[]
}

export interface DashboardUpcomingEvent {
  title: string
  start_at: string
  end_at: string
}

export interface DashboardCalendar {
  today_events: number
  upcoming: DashboardUpcomingEvent[]
}

export interface DashboardSlack {
  messages_7d: number
  active_channels: number
}

/** Today's health roll-up. Every metric is absent when no snapshot reported it. */
export interface DashboardHealth {
  steps?: number
  active_minutes?: number
  calories?: number
  sleep_hours?: number
  distance_km?: number
  heart_rate_bpm?: number
  heart_points?: number
}

export interface WeeklyActivityPoint {
  date: string
  label: string
  steps: number
  calories: number
  distance_km: number
}

export interface DashboardGithub {
  connected: boolean
  username?: string | null
}

export interface DashboardJournal {
  has_today: boolean
  today_mood?: string | null
  streak: number
}

export interface DashboardStats {
  tasks: DashboardTasks
  calendar: DashboardCalendar
  slack: DashboardSlack
  health: DashboardHealth
  health_weekly: WeeklyActivityPoint[]
  github: DashboardGithub
  journal: DashboardJournal
}

/** Authenticated profile as returned by `GET /api/auth/me` (UserResponse). */
export interface DashboardUser {
  id: string
  email: string
  full_name?: string | null
}
