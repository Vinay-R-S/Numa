"use client"

import { HEART_METRIC_CARDS } from "../health.constants"
import type { HealthSnapshot } from "../health.types"
import { HeartMetricCard } from "./HeartMetricCard"

/** Heart rate and heart points, rendered from `HEART_METRIC_CARDS` in order. */
export function HeartMetricsSection({ snapshot }: { snapshot: HealthSnapshot | null }) {
  return (
    <section className="grid grid-cols-1 gap-3 lg:grid-cols-2">
      {HEART_METRIC_CARDS.map((metric) => (
        <HeartMetricCard
          key={metric.key}
          icon={metric.icon}
          label={metric.label}
          value={snapshot?.[metric.key] ?? null}
          unit={metric.unit}
          goal={metric.goal}
          helper={metric.helper}
          accent={metric.accent}
        />
      ))}
    </section>
  )
}
