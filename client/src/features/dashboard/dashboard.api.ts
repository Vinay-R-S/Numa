/**
 * Dashboard API (NUMA-113 P4, PLAN 21.2 / 22.2).
 *
 * Typed fetchers built on the shared `http` client, replacing the raw `fetch`
 * calls that lived in `lib/stores/dashboardStore.ts` and `home/page.tsx`.
 * Responses are validated with the feature's zod schemas.
 *
 * Both endpoints answer with JSON. `http` resolves a body-less or non-JSON 2xx
 * to `undefined` (a proxy that drops the content-type header is enough), which
 * would put `undefined` into the store and crash the next render, so
 * `expectBody` turns that into the endpoint's error.
 */
import { expectBody, http } from "@/lib/http"
import type { DashboardStats, DashboardUser } from "./dashboard.types"
import { dashboardStatsSchema, dashboardUserSchema } from "./dashboard.schema"

export function fetchDashboardStats(signal?: AbortSignal): Promise<DashboardStats> {
  const message = "Failed to load dashboard stats"
  return expectBody(
    http.get("/dashboard/stats", {
      signal,
      schema: dashboardStatsSchema,
      errorMessage: message,
    }),
    message
  )
}

export function fetchCurrentUser(signal?: AbortSignal): Promise<DashboardUser> {
  const message = "Failed to load profile"
  return expectBody(
    http.get("/auth/me", {
      signal,
      schema: dashboardUserSchema,
      errorMessage: message,
    }),
    message
  )
}
