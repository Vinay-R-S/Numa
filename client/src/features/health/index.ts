/**
 * Health feature module public surface (NUMA-116 P4, PLAN 5.3 / 21.2).
 */
export * from "./health.types"
export * from "./health.api"
export * from "./health.schema"
export * from "./health.utils"
export * from "./health.constants"

export { useHealth } from "./useHealth"
export type { UseHealthReturn } from "./useHealth"
export { useHealthAgent } from "./useHealthAgent"
export type { UseHealthAgentReturn } from "./useHealthAgent"

export { ActivityChart } from "./components/ActivityChart"
export { ActivityTrendsSection } from "./components/ActivityTrendsSection"
export { HealthAgentPanel } from "./components/HealthAgentPanel"
export { HealthPageHeader } from "./components/HealthPageHeader"
export { HealthScore } from "./components/HealthScore"
export { HeartMetricCard } from "./components/HeartMetricCard"
export { HeartMetricsSection } from "./components/HeartMetricsSection"
export { MetricCard } from "./components/MetricCard"
export { MetricCardGrid } from "./components/MetricCardGrid"
export { SleepCard } from "./components/SleepCard"
