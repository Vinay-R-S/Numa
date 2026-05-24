"use client"

import React, { useCallback, useEffect, useMemo, useRef, useState } from "react"
import { Area, AreaChart, CartesianGrid, XAxis, YAxis } from "recharts"
import {
  Activity,
  Bot,
  Flame,
  Footprints,
  Heart,
  HeartPulse,
  MapPin,
  Moon,
  RefreshCw,
  Send,
  Sparkles,
  Square,
  TrendingUp,
  X,
  Zap,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { HeaderActionButton } from "@/components/ui/header-action-button"
import { LiveDataPill } from "@/components/ui/live-data-pill"
import { AgentMessageContent } from "@/components/agents/AgentMessageContent"
import { ChartContainer, ChartTooltip, ChartTooltipContent, type ChartConfig } from "@/components/ui/chart"
import { useSessionMessages } from "@/lib/useSessionMessages"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  HealthAgentMessage,
  HealthIntraday,
  HealthSnapshot,
  HealthStatus,
  getHealthIntraday,
  getHealthSnapshots,
  getHealthStatus,
  sendHealthAgentCommand,
  syncAllHealth,
} from "@/components/health/healthApi"

// ── Helpers ─────────────────────────────────────────────────────────────────────

function formatNumber(n: number | null | undefined): string {
  if (n == null) return "-"
  return n >= 1000 ? n.toLocaleString() : String(Math.round(n * 10) / 10)
}

function pct(value: number | null, goal: number): number {
  if (!value) return 0
  return Math.min(100, Math.round((value / goal) * 100))
}

function localDateString(date = new Date()): string {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, "0")
  const day = String(date.getDate()).padStart(2, "0")
  return `${year}-${month}-${day}`
}

type WeeklyActivityMetric = "steps" | "calories" | "distance_km"
type ActivityChartMode = "day" | "week"

const WEEKLY_ACTIVITY_OPTIONS: Array<{
  key: WeeklyActivityMetric
  label: string
  unit: string
  color: string
  icon: React.ElementType
}> = [
  { key: "steps", label: "Steps", unit: "steps", color: "#22d3ee", icon: Footprints },
  { key: "calories", label: "Calories", unit: "kcal", color: "#fb923c", icon: Flame },
  { key: "distance_km", label: "Distance", unit: "km", color: "#c084fc", icon: MapPin },
]

function formatCompactValue(value: number, unit: string): string {
  if (unit === "km") return `${value.toFixed(1)} km`
  if (value >= 1000) return `${(value / 1000).toFixed(1)}k`
  return `${Math.round(value).toLocaleString()}`
}

function lastSevenDays(): Date[] {
  return Array.from({ length: 7 }, (_, index) => {
    const date = new Date()
    date.setDate(date.getDate() - (6 - index))
    return date
  })
}

function isAbortError(error: unknown): boolean {
  return error instanceof DOMException && error.name === "AbortError"
}

function formatDateLabel(dateKey: string): string {
  const today = localDateString()
  const yesterdayDate = new Date()
  yesterdayDate.setDate(yesterdayDate.getDate() - 1)
  const yesterday = localDateString(yesterdayDate)

  if (dateKey === today) return "Today"
  if (dateKey === yesterday) return "Yesterday"

  const parsed = new Date(`${dateKey}T00:00:00`)
  return parsed.toLocaleDateString([], { month: "short", day: "numeric" })
}

type SleepStage = "generic" | "light" | "deep" | "rem"

type SleepTimelineSegment = {
  startMs: number
  endMs: number
  stage: SleepStage
  hours: number
}

const SLEEP_STAGE_META: Record<SleepStage, { label: string; fill: string; dot: string; priority: number }> = {
  deep: { label: "Deep", fill: "bg-indigo-500", dot: "bg-indigo-500", priority: 4 },
  rem: { label: "REM", fill: "bg-purple-500", dot: "bg-purple-500", priority: 3 },
  light: { label: "Light", fill: "bg-blue-500", dot: "bg-blue-500", priority: 2 },
  generic: { label: "Asleep", fill: "bg-slate-500", dot: "bg-slate-500", priority: 1 },
}

function readNumber(value: unknown): number | null {
  if (typeof value === "number" && Number.isFinite(value)) return value
  if (typeof value === "string" && value.trim()) {
    const parsed = Number(value)
    return Number.isFinite(parsed) ? parsed : null
  }
  return null
}

function normalizeSleepStage(value: unknown): SleepStage {
  const stage = typeof value === "string" ? value.toLowerCase() : "generic"
  return stage === "light" || stage === "deep" || stage === "rem" ? stage : "generic"
}

function formatSleepDuration(hours: number): string {
  const safeHours = Math.max(0, hours)
  const wholeHours = Math.floor(safeHours)
  const minutes = Math.round((safeHours - wholeHours) * 60)
  if (minutes === 60) return `${wholeHours + 1}h 0m`
  return `${wholeHours}h ${minutes}m`
}

function formatSleepTime(ms: number | null): string {
  if (!ms) return "-"
  return new Date(ms).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
}

function parseSleepTimestamp(value: string | null | undefined): number | null {
  if (!value) return null
  const parsed = new Date(value).getTime()
  return Number.isFinite(parsed) ? parsed : null
}

function normalizeSleepSegments(rawSegments: Array<Record<string, unknown>> | null | undefined): SleepTimelineSegment[] {
  const segments = (rawSegments || [])
    .map((segment) => {
      const startMs = readNumber(segment.start_ms)
      const endMs = readNumber(segment.end_ms)
      if (startMs == null || endMs == null || endMs <= startMs) return null
      return {
        startMs,
        endMs,
        stage: normalizeSleepStage(segment.stage),
      }
    })
    .filter((segment): segment is { startMs: number; endMs: number; stage: SleepStage } => Boolean(segment))

  if (segments.length === 0) return []

  const boundaries = Array.from(new Set(segments.flatMap((segment) => [segment.startMs, segment.endMs]))).sort((a, b) => a - b)
  const normalized: SleepTimelineSegment[] = []

  for (let index = 0; index < boundaries.length - 1; index += 1) {
    const startMs = boundaries[index]
    const endMs = boundaries[index + 1]
    const covering = segments.filter((segment) => segment.startMs < endMs && segment.endMs > startMs)
    if (covering.length === 0) continue
    const chosen = covering.reduce((best, segment) =>
      SLEEP_STAGE_META[segment.stage].priority > SLEEP_STAGE_META[best.stage].priority ? segment : best
    )
    const previous = normalized[normalized.length - 1]
    if (previous && previous.stage === chosen.stage && previous.endMs === startMs) {
      previous.endMs = endMs
      previous.hours = (previous.endMs - previous.startMs) / (1000 * 60 * 60)
    } else {
      normalized.push({
        startMs,
        endMs,
        stage: chosen.stage,
        hours: (endMs - startMs) / (1000 * 60 * 60),
      })
    }
  }

  return normalized
}

// ── Metric Card ─────────────────────────────────────────────────────────────────

function MetricCard({
  icon: Icon,
  label,
  value,
  unit,
  goal,
  color,
}: {
  icon: React.ElementType
  label: string
  value: number | null
  unit: string
  goal: number
  color: string
}) {
  const percentage = pct(value, goal)
  const remaining = goal - (value || 0)
  const goalMet = (value || 0) >= goal

  return (
    <div className="group relative rounded-2xl border border-border/40 bg-card/40 p-3 transition-all hover:-translate-y-1 hover:border-border/60 sm:p-5">
      <div className="flex items-center gap-2.5 mb-4">
        <div className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-lg ${color}`}>
          <Icon className="h-4 w-4 text-white" />
        </div>
        <div className="min-w-0">
          <p className="text-xs font-semibold text-muted-foreground truncate">{label}</p>
          <p className="text-[10px] text-muted-foreground/60 leading-none mt-0.5">
            Goal: {goal >= 1000 ? goal.toLocaleString() : goal} {unit}
          </p>
        </div>
      </div>

      <div className="flex items-center gap-3 sm:gap-4">
        {/* Circular progress */}
        <div className="relative shrink-0">
          <svg width={64} height={64} viewBox="0 0 80 80" className="sm:h-[80px] sm:w-[80px]" style={{ transform: "rotate(-90deg)" }}>
            <circle cx={40} cy={40} r={34} fill="none" stroke="currentColor" strokeWidth={6}
              className="text-border/20" />
            <circle cx={40} cy={40} r={34} fill="none" stroke="currentColor" strokeWidth={6}
              className={color.replace("bg-", "text-").replace("/80", "")}
              strokeLinecap="round"
              strokeDasharray={2 * Math.PI * 34}
              strokeDashoffset={2 * Math.PI * 34 * (1 - percentage / 100)}
              style={{ transition: "stroke-dashoffset 1s ease-out" }} />
          </svg>
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <span className="text-sm font-bold text-foreground tabular-nums">{percentage}</span>
            <span className="text-[9px] text-muted-foreground">%</span>
          </div>
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-baseline gap-1 mb-1">
            <span className="text-xl font-black text-foreground tabular-nums leading-none sm:text-2xl">
              {formatNumber(value)}
            </span>
            <span className="text-sm text-muted-foreground font-medium">{unit}</span>
          </div>
          <p className={`text-[10px] font-semibold ${goalMet ? "text-emerald-400" : "text-muted-foreground"}`}>
            {goalMet ? "Goal reached!" : `${formatNumber(remaining > 0 ? remaining : 0)} ${unit} to go`}
          </p>
        </div>
      </div>
    </div>
  )
}

// ── Weekly chart bar ────────────────────────────────────────────────────────────

function ActivityChart({
  snapshots,
  intraday,
  selectedDate,
  loading,
}: {
  snapshots: HealthSnapshot[]
  intraday: HealthIntraday | null
  selectedDate: string
  loading: boolean
}) {
  const [activeMetric, setActiveMetric] = useState<WeeklyActivityMetric>("steps")
  const [chartMode, setChartMode] = useState<ActivityChartMode>("day")

  const gfitDays = snapshots
    .filter((s) => s.source === "google_fit")
    .sort((a, b) => a.snapshot_date.localeCompare(b.snapshot_date))
  const snapshotsByDate = new Map(gfitDays.map((day) => [day.snapshot_date, day]))

  const DAY_NAMES = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
  const activeOption = WEEKLY_ACTIVITY_OPTIONS.find((option) => option.key === activeMetric) ?? WEEKLY_ACTIVITY_OPTIONS[0]
  const chartConfig = {
    value: {
      label: activeOption.label,
      color: activeOption.color,
    },
  } satisfies ChartConfig

  const weeklyChartData = lastSevenDays().map((date) => {
    const dateKey = localDateString(date)
    const snapshot = snapshotsByDate.get(dateKey)
    const value = Number(snapshot?.[activeMetric] || 0)
    return {
      date: dateKey,
      label: DAY_NAMES[date.getDay()],
      value,
      displayValue: formatCompactValue(value, activeOption.unit),
    }
  })

  const dailyChartData = (intraday?.buckets || []).map((bucket) => {
    const value = Number(bucket[activeMetric] || 0)
    return {
      date: selectedDate,
      label: bucket.label,
      range: bucket.range_label,
      value,
      displayValue: formatCompactValue(value, activeOption.unit),
    }
  })

  const chartData = chartMode === "day" ? dailyChartData : weeklyChartData

  const total = chartData.reduce((sum, day) => sum + day.value, 0)
  const bestDay = chartData.reduce((best, day) => (day.value > best.value ? day : best), chartData[0] || {
    label: "-",
    value: 0,
    displayValue: formatCompactValue(0, activeOption.unit),
  })

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
          <div className="inline-flex h-9 w-fit rounded-lg border border-border/40 bg-background/30 p-1">
            {[
              { key: "day" as const, label: "Day" },
              { key: "week" as const, label: "Week" },
            ].map((option) => (
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
              {formatCompactValue(total, activeOption.unit)}
            </p>
          </div>
          <div className="rounded-lg border border-border/30 bg-background/30 px-3 py-2">
            <p className="text-[10px] font-medium uppercase text-muted-foreground/70">Best</p>
            <p className="text-sm font-bold text-foreground tabular-nums">
              {bestDay.label} {bestDay.displayValue}
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
            tickFormatter={(value) => formatCompactValue(Number(value), activeOption.unit)}
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
                formatter={(value) => formatCompactValue(Number(value), activeOption.unit)}
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
      {chartMode === "day" && !loading && total === 0 && (
        <div className="rounded-lg border border-border/30 bg-background/30 px-3 py-2 text-xs text-muted-foreground">
          No cached hourly data for {formatDateLabel(selectedDate)} yet. Run Sync after Google Fit is connected.
        </div>
      )}
    </div>
  )
}

function HeartMetricCard({
  icon: Icon,
  label,
  value,
  unit,
  goal,
  helper,
  accent,
}: {
  icon: React.ElementType
  label: string
  value: number | null
  unit: string
  goal: number
  helper: string
  accent: {
    text: string
    stroke: string
    bg: string
    ring: string
  }
}) {
  const percentage = pct(value, goal)
  const displayValue = value == null ? "-" : formatNumber(value)

  return (
    <div className="rounded-2xl border border-border/40 bg-card/40 p-4 sm:p-5">
      <div className="flex items-center justify-between gap-4">
        <div className="min-w-0">
          <div className="mb-3 flex items-center gap-2">
            <div className={`flex h-9 w-9 items-center justify-center rounded-xl ${accent.bg} ${accent.ring}`}>
              <Icon className={`h-4 w-4 ${accent.text}`} />
            </div>
            <div>
              <p className="text-sm font-bold text-foreground">{label}</p>
              <p className="text-[11px] text-muted-foreground">{helper}</p>
            </div>
          </div>

          <div className="flex items-baseline gap-1.5">
            <span className={`text-3xl font-black tabular-nums ${accent.text}`}>
              {displayValue}
            </span>
            <span className="text-sm font-medium text-muted-foreground">{unit}</span>
          </div>
          <p className="mt-2 text-[11px] text-muted-foreground">
            {value == null ? "No heart data synced yet" : `${percentage}% of reference ${goal} ${unit}`}
          </p>
        </div>

        <div className="relative h-24 w-24 shrink-0 sm:h-28 sm:w-28">
          <svg viewBox="0 0 80 80" className="h-full w-full">
            <path
              d="M40 70C20 55 10 44 10 29C10 18 17 11 27 11C33 11 38 14 40 20C42 14 47 11 53 11C63 11 70 18 70 29C70 44 60 55 40 70Z"
              fill="currentColor"
              className="text-border/20"
            />
            <path
              d="M40 70C20 55 10 44 10 29C10 18 17 11 27 11C33 11 38 14 40 20C42 14 47 11 53 11C63 11 70 18 70 29C70 44 60 55 40 70Z"
              fill="none"
              stroke="currentColor"
              strokeWidth="4"
              strokeLinecap="round"
              strokeLinejoin="round"
              pathLength={100}
              strokeDasharray={100}
              strokeDashoffset={100 - percentage}
              className={accent.stroke}
            />
          </svg>
          <div className="absolute inset-0 flex items-center justify-center">
            <Icon className={`h-6 w-6 ${accent.text}`} />
          </div>
        </div>
      </div>
    </div>
  )
}

// ── Sleep card ───────────────────────────────────────────────────────────────────

function SleepCard({ snapshot }: { snapshot: HealthSnapshot | null }) {
  const sleep = snapshot?.sleep_hours

  if (!sleep || sleep <= 0) {
    return (
      <div className="flex flex-col items-center justify-center gap-3 rounded-2xl border border-border/40 bg-card/40 p-6 min-h-[200px]">
        <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-indigo-500/10">
          <Moon className="h-6 w-6 text-indigo-400/50" />
        </div>
        <p className="text-sm font-medium text-muted-foreground">No sleep data</p>
        <p className="text-xs text-muted-foreground/60 text-center max-w-[200px]">
          Sleep tracking must be enabled in Google Fit or a connected wearable.
        </p>
      </div>
    )
  }

  const goal = 8
  const normalizedSegments = normalizeSleepSegments(snapshot?.sleep_segments)
  const segmentHours = normalizedSegments.reduce((sum, segment) => sum + segment.hours, 0)
  const displaySleep = segmentHours > 0 ? segmentHours : sleep
  const rawSleepDiffers = segmentHours > 0 && Math.abs(sleep - segmentHours) >= 0.25
  const quality = Math.min(100, Math.round((displaySleep / goal) * 100))
  const sleepStart = normalizedSegments[0]?.startMs ?? parseSleepTimestamp(snapshot?.sleep_start_at)
  const sleepEnd = normalizedSegments[normalizedSegments.length - 1]?.endMs ?? parseSleepTimestamp(snapshot?.sleep_end_at)
  const timelineStart = sleepStart ?? 0
  const timelineEnd = sleepEnd ?? (timelineStart + displaySleep * 60 * 60 * 1000)
  const timelineSpan = Math.max(timelineEnd - timelineStart, displaySleep * 60 * 60 * 1000, 1)
  const timelineSegments = normalizedSegments.length > 0
    ? normalizedSegments
    : [{ startMs: timelineStart, endMs: timelineEnd, stage: "generic" as SleepStage, hours: displaySleep }]
  const longWindow = displaySleep > 12
  const stageTotals = timelineSegments.reduce<Record<SleepStage, number>>((acc, segment) => {
    acc[segment.stage] += segment.hours
    return acc
  }, { generic: 0, light: 0, deep: 0, rem: 0 })
  const stageList = (["deep", "rem", "light", "generic"] as SleepStage[])
    .map((stage) => ({ stage, hours: stageTotals[stage], ...SLEEP_STAGE_META[stage] }))
    .filter((stage) => stage.hours > 0)
  const sleepStatus = longWindow ? "Review" : quality >= 85 ? "On target" : quality >= 65 ? "Close" : "Low"

  return (
    <div className="rounded-2xl border border-border/40 bg-card/40 p-5 sm:p-6">
      <div className="mb-5 flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-indigo-500/10 ring-1 ring-indigo-500/20">
            <Moon className="h-5 w-5 text-indigo-400" />
          </div>
          <div>
            <h3 className="text-base font-bold text-foreground">Sleep Analysis</h3>
            <p className="text-xs text-muted-foreground">Last night</p>
          </div>
        </div>
        <span className={`rounded-full border px-2.5 py-0.5 text-xs font-bold ${
          longWindow ? "border-amber-500/20 bg-amber-500/10 text-amber-300"
          : quality >= 85 ? "border-emerald-500/20 bg-emerald-500/10 text-emerald-400"
          : quality >= 65 ? "border-yellow-500/20 bg-yellow-500/10 text-yellow-400"
          : "border-orange-500/20 bg-orange-500/10 text-orange-400"
        }`}>
          {sleepStatus}
        </span>
      </div>

      <div className="mb-5 grid gap-2 sm:grid-cols-3">
        <div className="rounded-xl border border-border/30 bg-background/30 px-3 py-2.5">
          <p className="text-[10px] font-medium uppercase text-muted-foreground/70">Duration</p>
          <p className="text-2xl font-black text-indigo-300 tabular-nums">{formatSleepDuration(displaySleep)}</p>
          {rawSleepDiffers && (
            <p className="mt-1 text-[10px] text-amber-300">Adjusted from {formatSleepDuration(sleep)}</p>
          )}
        </div>
        <div className="rounded-xl border border-border/30 bg-background/30 px-3 py-2.5">
          <p className="text-[10px] font-medium uppercase text-muted-foreground/70">Window</p>
          <p className="text-lg font-bold text-foreground tabular-nums">
            {formatSleepTime(sleepStart)} to {formatSleepTime(sleepEnd)}
          </p>
          <p className="mt-1 text-[10px] text-muted-foreground">{formatSleepDuration(goal)} goal</p>
        </div>
        <div className="rounded-xl border border-border/30 bg-background/30 px-3 py-2.5">
          <p className="text-[10px] font-medium uppercase text-muted-foreground/70">Goal</p>
          <p className="text-2xl font-black text-foreground tabular-nums">{quality}%</p>
          <p className="mt-1 text-[10px] text-muted-foreground">{formatSleepDuration(Math.max(goal - displaySleep, 0))} remaining</p>
        </div>
      </div>

      <div className="space-y-2">
        <div className="flex items-center justify-between text-[10px] font-medium uppercase text-muted-foreground/70">
          <span>Sleep timeline</span>
          <span>{formatSleepDuration(displaySleep)}</span>
        </div>
        <div className="relative h-12 overflow-hidden rounded-xl border border-border/30 bg-background/40">
          <div className="absolute inset-x-0 bottom-0 h-px bg-border/40" />
          {timelineSegments.map((segment, index) => {
            const left = ((segment.startMs - timelineStart) / timelineSpan) * 100
            const width = ((segment.endMs - segment.startMs) / timelineSpan) * 100
            return (
              <div
                key={`${segment.stage}-${segment.startMs}-${index}`}
                className={`absolute top-2 h-8 min-w-[3px] rounded-md ${SLEEP_STAGE_META[segment.stage].fill}`}
                style={{ left: `${Math.max(0, left)}%`, width: `${Math.max(1, width)}%` }}
                title={`${SLEEP_STAGE_META[segment.stage].label}: ${formatSleepDuration(segment.hours)}`}
              />
            )
          })}
        </div>
        <div className="flex items-center justify-between text-[11px] text-muted-foreground">
          <span>{formatSleepTime(sleepStart)}</span>
          <span>{formatSleepTime(sleepEnd)}</span>
        </div>
      </div>

      {stageList.length > 0 && (
        <div className="mt-4 grid grid-cols-2 gap-2 sm:grid-cols-4">
          {stageList.map((stage) => (
            <div key={stage.stage} className="rounded-lg border border-border/30 bg-background/30 p-2.5">
              <div className="mb-1 flex items-center gap-1.5">
                <div className={`h-2 w-2 rounded-full ${stage.dot}`} />
                <span className="text-[10px] text-muted-foreground">{stage.label}</span>
              </div>
              <p className="text-sm font-bold text-foreground tabular-nums">{formatSleepDuration(stage.hours)}</p>
            </div>
          ))}
        </div>
      )}

      {(longWindow || rawSleepDiffers) && (
        <div className="mt-4 rounded-lg border border-amber-500/20 bg-amber-500/10 px-3 py-2 text-xs text-amber-200">
          {longWindow
            ? "Google Fit returned a long sleep window. Re-sync after the watch app finishes uploading if this looks wrong."
            : "Overlapping synced sleep segments were collapsed into a single timeline."}
        </div>
      )}
    </div>
  )
}

// ── Health Score ─────────────────────────────────────────────────────────────────

function HealthScore({ snapshot }: { snapshot: HealthSnapshot | null }) {
  const steps = snapshot?.steps || 0
  const active = snapshot?.active_minutes || 0
  const cal = snapshot?.calories || 0
  const sleep = snapshot?.sleep_hours || 0

  const score = Math.round(
    Math.min(steps / 10000, 1) * 25 +
    Math.min(active / 60, 1) * 25 +
    Math.min(cal / 2500, 1) * 25 +
    Math.min(sleep / 8, 1) * 25
  )

  const level = score >= 75 ? "Excellent" : score >= 50 ? "Good" : score >= 25 ? "Fair" : "Needs Work"
  const color = score >= 75 ? "text-emerald-400" : score >= 50 ? "text-yellow-400" : score >= 25 ? "text-orange-400" : "text-red-400"
  const ringColor = score >= 75 ? "text-emerald-500" : score >= 50 ? "text-yellow-500" : score >= 25 ? "text-orange-500" : "text-red-500"

  return (
    <div className="rounded-2xl border border-border/40 bg-card/40 p-4 sm:p-6">
      <div className="flex flex-col items-center gap-4 sm:flex-row sm:items-center sm:gap-5">
        {/* Score ring */}
        <div className="relative shrink-0">
          <svg width={80} height={80} viewBox="0 0 100 100" className="sm:h-[100px] sm:w-[100px]" style={{ transform: "rotate(-90deg)" }}>
            <circle cx={50} cy={50} r={42} fill="none" stroke="currentColor" strokeWidth={8} className="text-border/20" />
            <circle cx={50} cy={50} r={42} fill="none" stroke="currentColor" strokeWidth={8}
              className={ringColor} strokeLinecap="round"
              strokeDasharray={2 * Math.PI * 42}
              strokeDashoffset={2 * Math.PI * 42 * (1 - score / 100)}
              style={{ transition: "stroke-dashoffset 1.2s ease-out" }} />
          </svg>
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <span className={`text-3xl font-black tabular-nums ${color}`}>{score}</span>
            <span className="text-[9px] text-muted-foreground">Health</span>
          </div>
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-3 mb-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-primary/10 ring-1 ring-primary/20">
              <Heart className="h-5 w-5 text-primary" />
            </div>
            <div>
              <h2 className="text-lg font-extrabold text-foreground leading-none">Your Daily Health</h2>
              <p className="text-xs text-muted-foreground mt-0.5">Based on selected day activity</p>
            </div>
          </div>
          <div className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-bold ${
            score >= 75 ? "border-emerald-500/20 bg-emerald-500/10 text-emerald-400"
            : score >= 50 ? "border-yellow-500/20 bg-yellow-500/10 text-yellow-400"
            : "border-orange-500/20 bg-orange-500/10 text-orange-400"
          }`}>
            {level}
          </div>

          <div className="mt-3 w-full h-2 bg-border/20 rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full transition-all bg-linear-to-r ${
                score >= 75 ? "from-emerald-500 to-green-400"
                : score >= 50 ? "from-yellow-500 to-amber-400"
                : "from-orange-500 to-red-400"
              }`}
              style={{ width: `${score}%` }}
            />
          </div>
        </div>
      </div>
    </div>
  )
}

// ── Chat Bubble ─────────────────────────────────────────────────────────────────

function ChatBubble({ msg }: { msg: HealthAgentMessage }) {
  const isUser = msg.role === "user"
  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      {!isUser && (
        <div className="mr-2 mt-1 flex h-6 w-6 shrink-0 items-center justify-center rounded-md bg-primary/10">
          <Bot className="h-3.5 w-3.5 text-primary" />
        </div>
      )}
      <div className={`min-w-0 max-w-[85%] overflow-hidden rounded-2xl px-4 py-2.5 text-sm leading-relaxed ${
        isUser ? "bg-primary/15 text-foreground rounded-br-sm" : "bg-muted/50 text-foreground rounded-bl-sm"
      }`}>
        <AgentMessageContent content={msg.content} />
      </div>
    </div>
  )
}

// ── Main Page ───────────────────────────────────────────────────────────────────

export default function HealthPage() {
  const [status, setStatus] = useState<HealthStatus | null>(null)
  const [snapshots, setSnapshots] = useState<HealthSnapshot[]>([])
  const [intraday, setIntraday] = useState<HealthIntraday | null>(null)
  const [intradayLoading, setIntradayLoading] = useState(false)
  const [loading, setLoading] = useState(true)
  const [syncing, setSyncing] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [selectedDate, setSelectedDate] = useState(localDateString())

  // Agent panel
  const [agentOpen, setAgentOpen] = useState(false)
  const [chatMessages, setChatMessages] = useSessionMessages<HealthAgentMessage>("numa:session:health-agent-chat", [
    { role: "assistant", content: "Hi! I'm your NUMA Health agent. I can show your fitness data, weekly trends, and personalized insights from Google Fit and Strava. What would you like to know?" },
  ])
  const [chatInput, setChatInput] = useState("")
  const [sending, setSending] = useState(false)
  const [chatError, setChatError] = useState<string | null>(null)
  const chatEndRef = useRef<HTMLDivElement>(null)
  const chatAbortRef = useRef<AbortController | null>(null)

  // ── Load data ───────────────────────────────────────────────────────────────

  const loadData = useCallback(async () => {
    setLoading(true)
    try {
      const [s, snaps] = await Promise.all([getHealthStatus(), getHealthSnapshots({ days: 8 })])
      setStatus(s)
      setSnapshots(snaps)
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load health data")
    } finally {
      setLoading(false)
    }
  }, [])

  const handleSync = useCallback(async () => {
    setSyncing(true)
    try {
      const result = await syncAllHealth()
      await loadData()
      if (!result.ok) {
        setError(result.detail || "No recent health data was returned from Google Fit or Strava")
      } else if (result.detail) {
        setError(null)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to sync health data")
    } finally {
      setSyncing(false)
    }
  }, [loadData])

  useEffect(() => {
    loadData()
  }, [loadData])

  useEffect(() => {
    let cancelled = false
    setIntradayLoading(true)
    getHealthIntraday({ snapshotDate: selectedDate })
      .then((data) => {
        if (!cancelled) setIntraday(data)
      })
      .catch(() => {
        if (!cancelled) setIntraday(null)
      })
      .finally(() => {
        if (!cancelled) setIntradayLoading(false)
      })

    return () => {
      cancelled = true
    }
  }, [selectedDate, snapshots])

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [chatMessages])

  useEffect(() => {
    if (!agentOpen) return

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setAgentOpen(false)
      }
    }

    window.addEventListener("keydown", onKeyDown)
    return () => window.removeEventListener("keydown", onKeyDown)
  }, [agentOpen])

  // ── Chat ──────────────────────────────────────────────────────────────────────

  const handleSend = async () => {
    const q = chatInput.trim()
    if (!q || sending) return
    const controller = new AbortController()
    chatAbortRef.current = controller
    const next: HealthAgentMessage[] = [...chatMessages, { role: "user", content: q }]
    setChatMessages(next)
    setChatInput("")
    setSending(true)
    setChatError(null)
    try {
      const result = await sendHealthAgentCommand(q, next, controller.signal)
      setChatMessages((prev) => [...prev, { role: "assistant", content: result.response }])
      if (result.refresh_health) void loadData()
    } catch (err) {
      if (isAbortError(err)) {
        setChatMessages((prev) => [...prev, { role: "assistant", content: "Generation stopped." }])
        return
      }
      const msg = err instanceof Error ? err.message : "Request failed"
      setChatError(msg)
      setChatMessages((prev) => [...prev, { role: "assistant", content: `Error: ${msg}` }])
    } finally {
      if (chatAbortRef.current === controller) {
        chatAbortRef.current = null
      }
      setSending(false)
    }
  }

  const handleStop = () => {
    chatAbortRef.current?.abort()
  }

  const canSend = useMemo(() => chatInput.trim().length > 0 && !sending, [chatInput, sending])

  // ── Derived data ──────────────────────────────────────────────────────────────

  const todayStr = localDateString()
  const availableDates = useMemo(() => {
    const dates = Array.from(new Set(snapshots.map((snapshot) => snapshot.snapshot_date)))
      .sort((a, b) => b.localeCompare(a))

    return dates.length > 0 ? dates : [todayStr]
  }, [snapshots, todayStr])
  const selectedGfit = snapshots.find((s) => s.source === "google_fit" && s.snapshot_date === selectedDate) || null
  const isLive = snapshots.length > 0
  const isConfigured = Boolean(status?.google_fit_configured || status?.strava_configured)

  useEffect(() => {
    if (!availableDates.includes(selectedDate)) {
      setSelectedDate(availableDates[0] ?? todayStr)
    }
  }, [availableDates, selectedDate, todayStr])

  // ── Render ────────────────────────────────────────────────────────────────────

  return (
    <div className="flex h-full w-full flex-col gap-4 overflow-y-auto px-4 py-4 sm:px-6 sm:py-6">

      {/* Header */}
      <header className="flex flex-col gap-3 rounded-2xl border border-border/40 bg-card/40 p-4 sm:flex-row sm:items-center sm:justify-between sm:p-5">
        <div className="flex items-center gap-3">
          <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-muted/30 ring-1 ring-border/50">
            <Activity className="h-5 w-5 text-foreground" />
          </div>
          <div>
            <h1 className="text-xl font-bold tracking-tight text-foreground sm:text-2xl">
              Health Dashboard
            </h1>
            <p className="text-xs text-muted-foreground sm:text-sm">
              Google Fit + Strava &bull; 7-day rolling window &bull; Synced to Supabase
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Select value={selectedDate} onValueChange={setSelectedDate}>
            <SelectTrigger className="h-9 w-[142px] border-border/40 bg-background/40 text-xs">
              <SelectValue placeholder="Select day" />
            </SelectTrigger>
            <SelectContent>
              {availableDates.map((dateKey) => (
                <SelectItem key={dateKey} value={dateKey}>
                  {formatDateLabel(dateKey)}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <LiveDataPill live={isLive} loading={loading} configured={isConfigured} />
          <HeaderActionButton
            icon={RefreshCw}
            label="Sync"
            loading={syncing}
            onClick={() => void handleSync()}
          >
            {syncing ? "Syncing..." : "Sync"}
          </HeaderActionButton>
          <HeaderActionButton
            icon={RefreshCw}
            label="Refresh"
            loading={loading}
            onClick={() => void loadData()}
          />
          <HeaderActionButton
            icon={Sparkles}
            label="Agent"
            active={agentOpen}
            onClick={() => setAgentOpen((v) => !v)}
          />
        </div>
      </header>

      {error && (
        <div className="rounded-xl border border-destructive/20 bg-destructive/5 px-4 py-3 text-sm text-destructive">
          {error}
        </div>
      )}

      {/* Health Score */}
      <HealthScore snapshot={selectedGfit} />

      {/* Heart Metrics */}
      <section className="grid grid-cols-1 gap-3 lg:grid-cols-2">
        <HeartMetricCard
          icon={HeartPulse}
          label="Heart Rate"
          value={selectedGfit?.heart_rate_bpm ?? null}
          unit="bpm"
          goal={120}
          helper="Daily average from Google Fit"
          accent={{
            text: "text-rose-400",
            stroke: "text-rose-400",
            bg: "bg-rose-500/10",
            ring: "ring-1 ring-rose-500/20",
          }}
        />
        <HeartMetricCard
          icon={Heart}
          label="Heart Points"
          value={selectedGfit?.heart_points ?? null}
          unit="pts"
          goal={30}
          helper="Move minutes with higher intensity"
          accent={{
            text: "text-pink-400",
            stroke: "text-pink-400",
            bg: "bg-pink-500/10",
            ring: "ring-1 ring-pink-500/20",
          }}
        />
      </section>

      {/* Metric Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
        <MetricCard icon={Footprints} label="Steps" value={selectedGfit?.steps ?? null}
          unit="steps" goal={10000} color="bg-cyan-500/80" />
        <MetricCard icon={Activity} label="Active Minutes" value={selectedGfit?.active_minutes ?? null}
          unit="min" goal={60} color="bg-emerald-500/80" />
        <MetricCard icon={Flame} label="Calories" value={selectedGfit?.calories ?? null}
          unit="kcal" goal={2500} color="bg-orange-500/80" />
        <MetricCard icon={MapPin} label="Distance" value={selectedGfit?.distance_km ?? null}
          unit="km" goal={8} color="bg-purple-500/80" />
        <MetricCard icon={Moon} label="Sleep" value={selectedGfit?.sleep_hours ?? null}
          unit="hrs" goal={8} color="bg-indigo-500/80" />
      </div>

      {/* Weekly Chart */}
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
        <ActivityChart snapshots={snapshots} intraday={intraday} selectedDate={selectedDate} loading={intradayLoading} />
      </section>

      {/* Sleep Analysis */}
      <SleepCard snapshot={selectedGfit} />

      {/* Floating Agent Panel */}
      {agentOpen && (
        <section className="fixed inset-x-3 bottom-3 top-auto z-40 flex max-h-[70vh] flex-col rounded-2xl border border-border/40 bg-card/95 p-3 shadow-2xl backdrop-blur-md sm:inset-auto sm:right-6 sm:bottom-6 sm:h-[min(70vh,640px)] sm:w-[min(420px,calc(100vw-3rem))] sm:p-4">

          {/* Chat header */}
          <div className="flex items-center gap-2 border-b border-border/40 px-1 pb-3 shrink-0">
            <div className="flex h-6 w-6 items-center justify-center rounded-md bg-primary/10">
              <Zap className="h-3.5 w-3.5 text-primary" />
            </div>
            <span className="text-sm font-semibold text-foreground">Health Agent</span>
            <span className="ml-auto rounded-full border border-border/30 bg-background/40 px-2 py-0.5 text-[10px] text-muted-foreground">
              Groq &bull; LangGraph
            </span>
            <button
              onClick={() => setAgentOpen(false)}
              className="ml-1 flex h-6 w-6 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
            >
              <X className="h-4 w-4" />
            </button>
          </div>

          {/* Quick actions */}
          <div className="border-b border-border/20 px-1 py-2 shrink-0">
            <div className="flex flex-wrap gap-1.5">
              {["How am I doing today?", "Show weekly trends", "Recommend a diet plan", "Suggest yoga for me", "Give me insights"].map((s) => (
                <button key={s} onClick={() => setChatInput(s)}
                  className="rounded-full border border-border/40 bg-background/40 px-2.5 py-1 text-[11px] text-muted-foreground transition-colors hover:border-primary/30 hover:bg-primary/5 hover:text-foreground">
                  {s}
                </button>
              ))}
            </div>
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto space-y-3 px-1 py-3 min-h-0">
            {chatMessages.map((msg, i) => (
              <ChatBubble key={`${msg.role}-${i}`} msg={msg} />
            ))}
            {sending && (
              <div className="flex items-start gap-2">
                <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-md bg-primary/10">
                  <Bot className="h-3.5 w-3.5 text-primary" />
                </div>
                <div className="rounded-2xl rounded-bl-sm bg-muted/50 px-4 py-3">
                  <div className="flex items-center gap-2">
                    <div className="flex gap-1">
                      <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-muted-foreground/50 [animation-delay:0ms]" />
                      <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-muted-foreground/50 [animation-delay:150ms]" />
                      <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-muted-foreground/50 [animation-delay:300ms]" />
                    </div>
                    <span className="text-xs text-muted-foreground">Thinking and generating output...</span>
                  </div>
                </div>
              </div>
            )}
            {chatError && (
              <p className="rounded-lg bg-destructive/10 px-3 py-2 text-xs text-destructive">{chatError}</p>
            )}
            <div ref={chatEndRef} />
          </div>

          {/* Input */}
          <div className="border-t border-border/40 px-1 pt-3 shrink-0">
            <div className="flex gap-2">
              <input
                value={chatInput}
                onChange={(e) => setChatInput(e.target.value)}
                onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); void handleSend() } }}
                placeholder="Ask the Health agent..."
                disabled={sending}
                className="flex-1 rounded-xl border border-border/40 bg-background px-3.5 py-2 text-sm text-foreground placeholder:text-muted-foreground/40 focus:outline-none focus:ring-1 focus:ring-primary/30 disabled:opacity-50"
              />
              <Button
                type="button"
                size="sm"
                variant={sending ? "destructive" : "default"}
                onClick={() => sending ? handleStop() : void handleSend()}
                disabled={!canSend && !sending}
                className="shrink-0"
              >
                {sending ? <Square className="h-4 w-4 sm:mr-1" /> : <Send className="h-4 w-4 sm:mr-1" />}
                <span className="hidden sm:inline">{sending ? "Stop" : "Send"}</span>
              </Button>
            </div>
          </div>
        </section>
      )}
    </div>
  )
}
