"use client"

import { useMemo, useState } from "react"
import { Area, AreaChart, CartesianGrid, XAxis, YAxis } from "recharts"

import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from "@/components/ui/chart"
import { DAY_NAMES, WEEKLY_ACTIVITY_OPTIONS } from "../health.constants"
import type {
  ActivityChartMode,
  ActivityChartPoint,
  HealthIntraday,
  HealthSnapshot,
  WeeklyActivityMetric,
} from "../health.types"
import { formatMetricValue, formatDateLabel, lastSevenDays, localDateString } from "../health.utils"

const CHART_MODES: Array<{ key: ActivityChartMode; label: string }> = [
  { key: "day", label: "Day" },
  { key: "week", label: "Week" },
]

interface ActivityChartProps {
  snapshots: HealthSnapshot[]
  intraday: HealthIntraday | null
  selectedDate: string
  loading: boolean
  error?: string | null
}

export function ActivityChart({
  snapshots,
  intraday,
  selectedDate,
  loading,
  error,
}: ActivityChartProps) {
  const [activeMetric, setActiveMetric] = useState<WeeklyActivityMetric>("steps")
  const [chartMode, setChartMode] = useState<ActivityChartMode>("day")

  const activeOption =
    WEEKLY_ACTIVITY_OPTIONS.find((option) => option.key === activeMetric) ?? WEEKLY_ACTIVITY_OPTIONS[0]

  const chartConfig = {
    value: {
      label: activeOption.label,
      color: activeOption.color,
    },
  } satisfies ChartConfig

  // `lastSevenDays()` reads the wall clock, so the window has to be part of the
  // memo key: without it a page left open past midnight keeps plotting
  // yesterday's seven days until a fetch replaces `snapshots`.
  const todayKey = localDateString()

  const weeklyChartData = useMemo<ActivityChartPoint[]>(() => {
    const snapshotsByDate = new Map(
      snapshots
        .filter((snapshot) => snapshot.source === "google_fit")
        .sort((a, b) => a.snapshot_date.localeCompare(b.snapshot_date))
        .map((snapshot) => [snapshot.snapshot_date, snapshot] as const)
    )

    // Anchored at local noon so stepping back seven days is DST-safe.
    return lastSevenDays(new Date(`${todayKey}T12:00:00`)).map((date) => {
      const dateKey = localDateString(date)
      const value = Number(snapshotsByDate.get(dateKey)?.[activeMetric] || 0)
      return {
        date: dateKey,
        label: DAY_NAMES[date.getDay()],
        value,
        displayValue: formatMetricValue(value, activeOption.unit),
      }
    })
  }, [snapshots, activeMetric, activeOption.unit, todayKey])

  const dailyChartData = useMemo<ActivityChartPoint[]>(
    () =>
      (intraday?.buckets || []).map((bucket) => {
        const value = Number(bucket[activeMetric] || 0)
        return {
          date: selectedDate,
          label: bucket.label,
          range: bucket.range_label,
          value,
          displayValue: formatMetricValue(value, activeOption.unit),
        }
      }),
    [intraday, selectedDate, activeMetric, activeOption.unit]
  )

  const chartData = chartMode === "day" ? dailyChartData : weeklyChartData

  const total = chartData.reduce((sum, point) => sum + point.value, 0)
  const bestPoint = chartData.reduce<ActivityChartPoint>(
    (best, point) => (point.value > best.value ? point : best),
    chartData[0] || {
      date: selectedDate,
      label: "-",
      value: 0,
      displayValue: formatMetricValue(0, activeOption.unit),
    }
  )

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
          <div className="inline-flex h-9 w-fit rounded-lg border border-border/40 bg-background/30 p-1">
            {CHART_MODES.map((option) => (
              <button
                key={option.key}
                type="button"
                aria-pressed={chartMode === option.key}
                onClick={() => setChartMode(option.key)}
                className={`h-7 rounded-md px-3 text-xs font-semibold transition-colors ${
                  chartMode === option.key
                    ? "bg-primary/15 text-foreground"
                    : "text-muted-foreground hover:text-foreground"
                }`}
              >
                {option.label}
              </button>
            ))}
          </div>

          <div className="flex items-center gap-2 overflow-x-auto pb-1 sm:pb-0">
            {WEEKLY_ACTIVITY_OPTIONS.map((option) => {
              const Icon = option.icon
              const selected = option.key === activeMetric

              return (
                <button
                  key={option.key}
                  type="button"
                  aria-pressed={selected}
                  onClick={() => setActiveMetric(option.key)}
                  className={`inline-flex h-9 shrink-0 items-center gap-2 rounded-lg border px-3 text-xs font-semibold transition-colors ${
                    selected
                      ? "border-primary/40 bg-primary/10 text-foreground"
                      : "border-border/40 bg-background/30 text-muted-foreground hover:border-border/70 hover:text-foreground"
                  }`}
                >
                  <Icon className="h-3.5 w-3.5" />
                  {option.label}
                </button>
              )
            })}
          </div>
        </div>

        <div className="grid grid-cols-2 gap-2 sm:min-w-56">
          <div className="rounded-lg border border-border/30 bg-background/30 px-3 py-2">
            <p className="text-[10px] font-medium uppercase text-muted-foreground/70">Total</p>
            <p className="text-sm font-bold text-foreground tabular-nums">
              {formatMetricValue(total, activeOption.unit)}
            </p>
          </div>
          <div className="rounded-lg border border-border/30 bg-background/30 px-3 py-2">
            <p className="text-[10px] font-medium uppercase text-muted-foreground/70">Best</p>
            <p className="text-sm font-bold text-foreground tabular-nums">
              {bestPoint.label} {bestPoint.displayValue}
            </p>
          </div>
        </div>
      </div>

      <ChartContainer config={chartConfig} className="h-64 w-full sm:h-72">
        <AreaChart data={chartData} margin={{ left: 12, right: 8, top: 12, bottom: 0 }}>
          <defs>
            <linearGradient id="weeklyActivityFill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="var(--color-value)" stopOpacity={0.32} />
              <stop offset="95%" stopColor="var(--color-value)" stopOpacity={0.02} />
            </linearGradient>
          </defs>
          <CartesianGrid vertical={false} strokeDasharray="4 4" />
          <XAxis
            dataKey="label"
            tickLine={false}
            axisLine={false}
            tickMargin={10}
            interval={chartMode === "day" ? 1 : 0}
            fontSize={11}
          />
          <YAxis
            width={58}
            tickLine={false}
            axisLine={false}
            fontSize={12}
            tickFormatter={(value) => formatMetricValue(Number(value), activeOption.unit)}
          />
          <ChartTooltip
            cursor={{ stroke: activeOption.color, strokeOpacity: 0.35, strokeWidth: 1 }}
            content={
              <ChartTooltipContent
                indicator="line"
                labelFormatter={(_, payload) => {
                  const payloadData = payload[0]?.payload
                  if (chartMode === "day" && typeof payloadData?.range === "string") {
                    return payloadData.range
                  }
                  const date = payloadData?.date
                  return typeof date === "string" ? date : activeOption.label
                }}
                formatter={(value) => formatMetricValue(Number(value), activeOption.unit)}
              />
            }
          />
          <Area
            dataKey="value"
            type="monotone"
            stroke="var(--color-value)"
            strokeWidth={3}
            fill="url(#weeklyActivityFill)"
            dot={{ r: 4, strokeWidth: 2, fill: "hsl(var(--card))", stroke: activeOption.color }}
            activeDot={{ r: 6, strokeWidth: 2, fill: activeOption.color, stroke: "hsl(var(--background))" }}
          />
        </AreaChart>
      </ChartContainer>

      {chartMode === "day" && !loading && error && (
        <div className="rounded-lg border border-destructive/20 bg-destructive/5 px-3 py-2 text-xs text-destructive">
          Could not load hourly data for {formatDateLabel(selectedDate)}: {error}
        </div>
      )}

      {chartMode === "day" && !loading && !error && total === 0 && (
        <div className="rounded-lg border border-border/30 bg-background/30 px-3 py-2 text-xs text-muted-foreground">
          No cached hourly data for {formatDateLabel(selectedDate)} yet. Run Sync after Google Fit is connected.
        </div>
      )}
    </div>
  )
}
