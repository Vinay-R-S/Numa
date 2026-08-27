/**
 * Dashboard feature module public surface (NUMA-113 P4, PLAN 5.3 / 21.2).
 *
 * Cross-page dashboard state lives in the `useDashboardStore` zustand store
 * (`lib/stores/dashboardStore.ts`) as the single source of truth (PLAN 9); it
 * consumes this module's api/types.
 */
export * from "./dashboard.types"
export * from "./dashboard.api"
export * from "./dashboard.schema"
export * from "./dashboard.utils"
export { ICON_COLORS, STAT_SKELETON_KEYS } from "./dashboard.constants"

export { useDashboard } from "./useDashboard"
export type { UseDashboardReturn } from "./useDashboard"

export { StatCard } from "./components/StatCard"
export { StatCardSkeleton } from "./components/StatCardSkeleton"
export { HealthRingCard } from "./components/HealthRingCard"
export { TaskDistributionChart } from "./components/TaskDistributionChart"
export { WeeklyActivityChart } from "./components/WeeklyActivityChart"
export { DashboardHeader } from "./components/DashboardHeader"
export { TaskStatsRow } from "./components/TaskStatsRow"
export { OverviewRow } from "./components/OverviewRow"
export { HealthSection } from "./components/HealthSection"
export { UpcomingEventsCard } from "./components/UpcomingEventsCard"
export { DeveloperCard } from "./components/DeveloperCard"
export { RecentTasksCard } from "./components/RecentTasksCard"
