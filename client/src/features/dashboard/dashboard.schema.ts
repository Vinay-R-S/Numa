/**
 * Dashboard validation schemas (NUMA-113 P4, PLAN 22.2 / 22.3).
 *
 * Mirrors the response shape assembled in `server/src/dashboard/router.py` and
 * the column nullability of the underlying tables (baseline migration): task
 * `priority`/`source_name`/`due_date`, `github.username` and `journal.mood` are
 * nullable, task/event titles are NOT NULL. Runs in `dashboard.api.ts` via the
 * shared `http` `schema` option so API contract drift fails loudly.
 *
 * The explicit `z.ZodType<...>` annotations keep these schemas and
 * `dashboard.types.ts` provably in sync at compile time.
 */
import { z } from "@/lib/validation"
import type { DashboardStats, DashboardUser } from "./dashboard.types"

export const dashboardRecentTaskSchema = z.object({
  title: z.string(),
  status: z.string(),
  priority: z.string().nullish(),
  due_date: z.string().nullish(),
  source_name: z.string().nullish(),
  created_at: z.string().nullish(),
})

export const dashboardTodayTasksSchema = z.object({
  total: z.number(),
  completed: z.number(),
  inprogress: z.number(),
  pending: z.number(),
})

export const dashboardUpcomingEventSchema = z.object({
  title: z.string(),
  start_at: z.string(),
  end_at: z.string(),
})

export const weeklyActivityPointSchema = z.object({
  date: z.string(),
  label: z.string(),
  steps: z.number(),
  calories: z.number(),
  distance_km: z.number(),
})

export const dashboardStatsSchema: z.ZodType<DashboardStats> = z.object({
  tasks: z.object({
    total: z.number(),
    completed: z.number(),
    inprogress: z.number(),
    pending: z.number(),
    today: dashboardTodayTasksSchema.optional(),
    streak: z.number(),
    recent: z.array(dashboardRecentTaskSchema),
  }),
  calendar: z.object({
    today_events: z.number(),
    upcoming: z.array(dashboardUpcomingEventSchema),
  }),
  slack: z.object({
    messages_7d: z.number(),
    active_channels: z.number(),
  }),
  health: z.object({
    steps: z.number().optional(),
    active_minutes: z.number().optional(),
    calories: z.number().optional(),
    sleep_hours: z.number().optional(),
    distance_km: z.number().optional(),
    heart_rate_bpm: z.number().optional(),
    heart_points: z.number().optional(),
  }),
  health_weekly: z.array(weeklyActivityPointSchema),
  github: z.object({
    connected: z.boolean(),
    username: z.string().nullish(),
  }),
  journal: z.object({
    has_today: z.boolean(),
    today_mood: z.string().nullish(),
    streak: z.number(),
  }),
})

export const dashboardUserSchema: z.ZodType<DashboardUser> = z.object({
  id: z.string(),
  email: z.string(),
  full_name: z.string().nullish(),
})
