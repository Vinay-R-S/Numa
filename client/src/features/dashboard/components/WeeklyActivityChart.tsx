"use client"

import { Area, AreaChart, CartesianGrid, XAxis, YAxis } from "recharts"
import { Activity } from "lucide-react"
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from "@/components/ui/chart"
import { cn } from "@/lib/utils"
import { ICON_COLORS } from "../dashboard.constants"
import type { WeeklyActivityPoint } from "../dashboard.types"
import { formatCompactValue, formatWeeklyMetric } from "../dashboard.utils"

const CHART_CONFIG = {
  steps: { label: "Steps", color: "#22d3ee" },
  calories: { label: "Calories", color: "#fb923c" },
  distance_km: { label: "Distance", color: "#c084fc" },
} satisfies ChartConfig

export function WeeklyActivityChart({ data }: { data: WeeklyActivityPoint[] }) {
  const totalSteps = data.reduce((sum, item) => sum + item.steps, 0)
  const totalCalories = data.reduce((sum, item) => sum + item.calories, 0)
  const totalDistance = data.reduce((sum, item) => sum + item.distance_km, 0)

  const legendItems = [
    { key: "steps", label: "Steps", color: "#22d3ee", value: formatCompactValue(totalSteps) },
    { key: "calories", label: "Calories", color: "#fb923c", value: `${formatCompactValue(totalCalories)} kcal` },
    { key: "distance_km", label: "Distance", color: "#c084fc", value: `${totalDistance.toFixed(1)} km` },
  ]

  return (
    <div className="rounded-xl border border-border/40 bg-card/40 p-4 sm:p-5">
      <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-2">
          <Activity className={cn("h-4 w-4", ICON_COLORS.active)} />
          <div>
            <span className="text-sm font-semibold text-foreground">Weekly Activity</span>
            <p className="text-[10px] text-muted-foreground">Last 7 days - steps, calories, and distance</p>
          </div>
        </div>
        <div className="grid gap-2 sm:grid-cols-3">
          {legendItems.map((item) => (
            <div key={item.key} className="rounded-lg border border-border/30 bg-background/30 px-3 py-1.5">
              <div className="flex items-center gap-1.5">
                <span className="h-2 w-2 rounded-full" style={{ backgroundColor: item.color }} />
                <p className="text-[10px] font-medium uppercase text-muted-foreground/70">{item.label}</p>
              </div>
              <p className="text-sm font-bold text-foreground tabular-nums">{item.value}</p>
            </div>
          ))}
        </div>
      </div>

      <ChartContainer config={CHART_CONFIG} className="h-60 w-full sm:h-64">
        <AreaChart data={data} margin={{ left: 10, right: 8, top: 12, bottom: 0 }}>
          <defs>
            <linearGradient id="homeWeeklyStepsFill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="var(--color-steps)" stopOpacity={0.3} />
              <stop offset="95%" stopColor="var(--color-steps)" stopOpacity={0.02} />
            </linearGradient>
            <linearGradient id="homeWeeklyCaloriesFill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="var(--color-calories)" stopOpacity={0.18} />
              <stop offset="95%" stopColor="var(--color-calories)" stopOpacity={0.01} />
            </linearGradient>
            <linearGradient id="homeWeeklyDistanceFill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="var(--color-distance_km)" stopOpacity={0.18} />
              <stop offset="95%" stopColor="var(--color-distance_km)" stopOpacity={0.01} />
            </linearGradient>
          </defs>
          <CartesianGrid vertical={false} strokeDasharray="4 4" />
          <XAxis dataKey="label" tickLine={false} axisLine={false} tickMargin={10} interval={0} fontSize={11} />
          <YAxis
            yAxisId="activity"
            width={54}
            tickLine={false}
            axisLine={false}
            fontSize={12}
            tickFormatter={(value) => formatCompactValue(Number(value))}
          />
          <YAxis
            yAxisId="distance"
            orientation="right"
            width={48}
            tickLine={false}
            axisLine={false}
            fontSize={12}
            tickFormatter={(value) => `${Number(value).toFixed(1)} km`}
          />
          <ChartTooltip
            cursor={{ stroke: "#22d3ee", strokeOpacity: 0.35, strokeWidth: 1 }}
            content={
              <ChartTooltipContent
                indicator="line"
                labelFormatter={(_, payload) => {
                  const date = payload[0]?.payload?.date
                  return typeof date === "string" ? date : "Steps"
                }}
                formatter={(value, name) => formatWeeklyMetric(Number(value), name)}
              />
            }
          />
          <Area
            dataKey="steps"
            yAxisId="activity"
            type="monotone"
            stroke="var(--color-steps)"
            strokeWidth={3}
            fill="url(#homeWeeklyStepsFill)"
            dot={{ r: 4, strokeWidth: 2, fill: "hsl(var(--card))", stroke: "#22d3ee" }}
            activeDot={{ r: 6, strokeWidth: 2, fill: "#22d3ee", stroke: "hsl(var(--background))" }}
          />
          <Area
            dataKey="calories"
            yAxisId="activity"
            type="monotone"
            stroke="var(--color-calories)"
            strokeWidth={2}
            fill="url(#homeWeeklyCaloriesFill)"
            dot={{ r: 3, strokeWidth: 2, fill: "hsl(var(--card))", stroke: "#fb923c" }}
            activeDot={{ r: 5, strokeWidth: 2, fill: "#fb923c", stroke: "hsl(var(--background))" }}
          />
          <Area
            dataKey="distance_km"
            yAxisId="distance"
            type="monotone"
            stroke="var(--color-distance_km)"
            strokeWidth={2}
            fill="url(#homeWeeklyDistanceFill)"
            dot={{ r: 3, strokeWidth: 2, fill: "hsl(var(--card))", stroke: "#c084fc" }}
            activeDot={{ r: 5, strokeWidth: 2, fill: "#c084fc", stroke: "hsl(var(--background))" }}
          />
        </AreaChart>
      </ChartContainer>
    </div>
  )
}
