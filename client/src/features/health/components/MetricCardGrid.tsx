"use client"

import { METRIC_CARDS } from "../health.constants"
import type { HealthSnapshot } from "../health.types"
import { MetricCard } from "./MetricCard"

/** The five daily progress cards, rendered from `METRIC_CARDS` in order. */
export function MetricCardGrid({ snapshot }: { snapshot: HealthSnapshot | null }) {
  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
      {METRIC_CARDS.map((metric) => (
        <MetricCard
          key={metric.key}
          icon={metric.icon}
          label={metric.label}
          value={snapshot?.[metric.key] ?? null}
          unit={metric.unit}
          goal={metric.goal}
          color={metric.color}
        />
      ))}
    </div>
  )
}
