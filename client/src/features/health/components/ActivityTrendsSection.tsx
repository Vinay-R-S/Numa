"use client"

import { TrendingUp } from "lucide-react"

import type { HealthIntraday, HealthSnapshot } from "../health.types"
import { ActivityChart } from "./ActivityChart"

interface ActivityTrendsSectionProps {
  snapshots: HealthSnapshot[]
  intraday: HealthIntraday | null
  selectedDate: string
  intradayLoading: boolean
  intradayError?: string | null
}

export function ActivityTrendsSection({
  snapshots,
  intraday,
  selectedDate,
  intradayLoading,
  intradayError,
}: ActivityTrendsSectionProps) {
  return (
    <section className="rounded-2xl border border-border/40 bg-card/40 p-5">
      <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-cyan-500/10 ring-1 ring-cyan-500/20">
            <TrendingUp className="h-5 w-5 text-cyan-400" />
          </div>
          <div>
            <h3 className="text-base font-bold text-foreground">Activity Trends</h3>
            <p className="text-xs text-muted-foreground">Selected day 6 AM to 10 PM or last 7 days</p>
          </div>
        </div>
        <div className="min-h-5 text-xs text-muted-foreground">
          {intradayLoading ? "Loading day data..." : ""}
        </div>
      </div>

      <ActivityChart
        snapshots={snapshots}
        intraday={intraday}
        selectedDate={selectedDate}
        loading={intradayLoading}
        error={intradayError}
      />
    </section>
  )
}
