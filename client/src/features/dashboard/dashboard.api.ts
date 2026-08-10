/**
 * Dashboard API (NUMA-113 P4, PLAN 21.2 / 22.2).
 *
 * Typed fetchers built on the shared `http` client, replacing the raw `fetch`
 * calls that lived in `lib/stores/dashboardStore.ts` and `home/page.tsx`.
 * Responses are validated with the feature's zod schemas.
 */
import { http } from "@/lib/http"
import type { DashboardStats, DashboardUser } from "./dashboard.types"
import { dashboardStatsSchema, dashboardUserSchema } from "./dashboard.schema"

export function fetchDashboardStats(signal?: AbortSignal): Promise<DashboardStats> {
  return http.get("/dashboard/stats", {
    signal,
    schema: dashboardStatsSchema,
    errorMessage: "Failed to load dashboard stats",
  })
}

export function fetchCurrentUser(signal?: AbortSignal): Promise<DashboardUser> {
  return http.get("/auth/me", {
    signal,
    schema: dashboardUserSchema,
    errorMessage: "Failed to load profile",
  })
}
