"use client"

import React, { useEffect, useRef, useState } from "react"
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Cell,
  PieChart,
  Pie,
  Tooltip as RechartsTooltip,
  Legend,
} from "recharts"
import {
  CheckCircle2,
  TrendingUp,
  Flame,
  ListTodo,
  Clock,
  AlertCircle,
  BarChart2,
} from "lucide-react"
import { format, parseISO } from "date-fns"
import type { TaskStats } from "../tasks.types"
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Skeleton } from "@/components/ui/skeleton"
import { cn } from "@/lib/utils"

const PERIOD_LABELS: Record<string, string> = {
  daily: "Last 30 Days",
  weekly: "Last 12 Weeks",
  monthly: "Last 12 Months",
  yearly: "All Time",
}

const STATUS_COLORS: Record<string, string> = {
  planned: "#60a5fa",
  inprogress: "#fbbf24",
  completed: "#34d399",
  pending: "#f87171",
}

const STATUS_LABELS: Record<string, string> = {
  planned: "Planned",
  inprogress: "In Progress",
  completed: "Completed",
  pending: "Pending",
}

function MeasuredChartFrame({
  className,
  children,
}: {
  className: string
  children: (size: { width: number; height: number }) => React.ReactNode
}) {
  const ref = useRef<HTMLDivElement | null>(null)
  const [size, setSize] = useState<{ width: number; height: number } | null>(null)

  useEffect(() => {
    const node = ref.current
    if (!node) return

    const updateSize = (width: number, height: number) => {
      const next = {
        width: Math.floor(width),
        height: Math.floor(height),
      }
      setSize((current) =>
        current?.width === next.width && current?.height === next.height ? current : next
      )
    }

    const rect = node.getBoundingClientRect()
    updateSize(rect.width, rect.height)

    const observer = new ResizeObserver(([entry]) => {
      const box = entry.contentRect
      updateSize(box.width, box.height)
    })
    observer.observe(node)
    return () => observer.disconnect()
  }, [])

  return (
    <div ref={ref} className={className}>
      {size && size.width > 0 && size.height > 0 ? children(size) : null}
    </div>
  )
}

function formatDateLabel(date: string, period: string): string {
  try {
    const d = parseISO(date)
    if (period === "daily") return format(d, "MMM d")
    if (period === "weekly") return `Wk ${format(d, "w")}`
    if (period === "monthly") return format(d, "MMM yy")
    if (period === "yearly") return date
    return date
  } catch {
    return date
  }
}

interface StatCardProps {
  icon: React.ReactNode
  label: string
  value: number | string
  color?: string
  sub?: string
}

function StatCard({ icon, label, value, color, sub }: StatCardProps) {
  return (
    <div className="rounded-2xl border border-border/50 bg-card p-4 flex flex-col gap-2">
      <div className="flex items-center justify-between">
        <span className="text-sm text-muted-foreground">{label}</span>
        <span className={cn("opacity-80", color)}>{icon}</span>
      </div>
      <div className="text-3xl font-bold text-foreground tracking-tight">{value}</div>
      {sub && <div className="text-xs text-muted-foreground">{sub}</div>}
    </div>
  )
}

interface AnalyticsDashboardProps {
  stats: TaskStats | null
  loading: boolean
}

export function AnalyticsDashboard({ stats, loading }: AnalyticsDashboardProps) {
  const [period, setPeriod] = useState<"daily" | "weekly" | "monthly" | "yearly">("daily")

  const completedCount =
    stats?.by_status.find((s) => s.status === "completed")?.count ?? 0
  const inProgressCount =
    stats?.by_status.find((s) => s.status === "inprogress")?.count ?? 0
  const pendingCount =
    stats?.by_status.find((s) => s.status === "pending")?.count ?? 0

  const periodData = stats?.[period] ?? []
  const chartData = periodData.map((item) => ({
    ...item,
    label: formatDateLabel(item.date, period),
  }))

  const pieData = stats?.by_status.map((s) => ({
    name: STATUS_LABELS[s.status] ?? s.status,
    value: s.count,
    fill: STATUS_COLORS[s.status] ?? "#64748b",
  })) ?? []

  // Only show the skeleton on the very first load; once data exists, refresh in-place
  if (loading && !stats) {
    return (
      <div className="space-y-6">
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          {[...Array(4)].map((_, i) => (
            <Skeleton key={i} className="h-28 rounded-2xl" />
          ))}
        </div>
        <Skeleton className="h-64 rounded-2xl" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Section Header */}
      <div className="flex items-center gap-3">
        <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-primary/10">
          <BarChart2 className="h-5 w-5 text-primary" />
        </div>
        <div>
          <h2 className="text-xl font-bold">Analytics</h2>
          <p className="text-sm text-muted-foreground">Your productivity at a glance</p>
        </div>
      </div>

      {/* Stat Cards */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-5">
        <StatCard
          icon={<ListTodo className="h-5 w-5" />}
          label="Total Tasks"
          value={stats?.total ?? 0}
          sub="all time"
        />
        <StatCard
          icon={<CheckCircle2 className="h-5 w-5" />}
          label="Completed"
          value={completedCount}
          color="text-emerald-400"
          sub="done"
        />
        <StatCard
          icon={<TrendingUp className="h-5 w-5" />}
          label="In Progress"
          value={inProgressCount}
          color="text-amber-400"
          sub="active"
        />
        <StatCard
          icon={<AlertCircle className="h-5 w-5" />}
          label="Pending"
          value={pendingCount}
          color="text-rose-400"
          sub="blocked"
        />
        <StatCard
          icon={<Flame className="h-5 w-5" />}
          label="Current Streak"
          value={`${stats?.streak ?? 0}d`}
          color="text-orange-400"
          sub="consecutive days"
        />
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Completion Bar Chart */}
        <div className="min-w-0 rounded-2xl border border-border/50 bg-card p-5 lg:col-span-2">
          <div className="mb-4 flex items-center justify-between">
            <h3 className="font-semibold text-sm text-foreground">Tasks Completed</h3>
            <Tabs
              value={period}
              onValueChange={(v) =>
                setPeriod(v as "daily" | "weekly" | "monthly" | "yearly")
              }
            >
              <TabsList className="h-8 text-xs">
                <TabsTrigger value="daily" className="text-xs px-2 py-0.5">Day</TabsTrigger>
                <TabsTrigger value="weekly" className="text-xs px-2 py-0.5">Week</TabsTrigger>
                <TabsTrigger value="monthly" className="text-xs px-2 py-0.5">Month</TabsTrigger>
                <TabsTrigger value="yearly" className="text-xs px-2 py-0.5">Year</TabsTrigger>
              </TabsList>
            </Tabs>
          </div>

          {chartData.length === 0 ? (
            <div className="flex h-48 items-center justify-center text-sm text-muted-foreground">
              No completed tasks in {PERIOD_LABELS[period].toLowerCase()} yet
            </div>
          ) : (
            <MeasuredChartFrame className="h-52 w-full min-w-0">
              {({ width, height }) => (
                <BarChart
                  data={chartData}
                  height={height}
                  margin={{ top: 4, right: 8, bottom: 0, left: -16 }}
                  width={width}
                >
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="rgba(255,255,255,0.05)" />
                  <XAxis
                    dataKey="label"
                    tick={{ fill: "var(--color-muted-foreground)", fontSize: 11 }}
                    axisLine={false}
                    tickLine={false}
                    interval="preserveStartEnd"
                  />
                  <YAxis
                    tick={{ fill: "var(--color-muted-foreground)", fontSize: 11 }}
                    axisLine={false}
                    tickLine={false}
                    allowDecimals={false}
                  />
                  <RechartsTooltip
                    contentStyle={{
                      backgroundColor: "var(--card)",
                      border: "1px solid var(--border)",
                      borderRadius: 8,
                      fontSize: 12,
                    }}
                    formatter={(value) => [value, "Tasks"]}
                  />
                  <Bar dataKey="count" radius={[4, 4, 0, 0]} maxBarSize={40}>
                    {chartData.map((_, i) => (
                      <Cell
                        key={i}
                        fill={`hsl(${160 + i * 3}, 70%, 55%)`}
                      />
                    ))}
                  </Bar>
                </BarChart>
              )}
            </MeasuredChartFrame>
          )}
        </div>

        {/* Status Donut */}
        <div className="min-w-0 rounded-2xl border border-border/50 bg-card p-5">
          <h3 className="mb-4 font-semibold text-sm text-foreground">Status Breakdown</h3>
          {pieData.length === 0 || pieData.every((d) => d.value === 0) ? (
            <div className="flex h-48 items-center justify-center text-sm text-muted-foreground">
              No tasks yet
            </div>
          ) : (
            <MeasuredChartFrame className="h-[200px] w-full min-w-0">
              {({ width, height }) => (
                <PieChart height={height} width={width}>
                  <Pie
                    data={pieData}
                    innerRadius={50}
                    outerRadius={80}
                    paddingAngle={3}
                    dataKey="value"
                  >
                    {pieData.map((entry, index) => (
                      <Cell key={index} fill={entry.fill} />
                    ))}
                  </Pie>
                  <RechartsTooltip
                    contentStyle={{
                      backgroundColor: "var(--card)",
                      border: "1px solid var(--border)",
                      borderRadius: 8,
                      fontSize: 12,
                    }}
                  />
                  <Legend
                    formatter={(value) => (
                      <span style={{ fontSize: 11, color: "var(--muted-foreground)" }}>
                        {value}
                      </span>
                    )}
                  />
                </PieChart>
              )}
            </MeasuredChartFrame>
          )}

          {/* Legend with counts */}
          <div className="mt-3 space-y-1.5">
            {pieData.map((d) => (
              <div key={d.name} className="flex items-center justify-between text-xs">
                <div className="flex items-center gap-2">
                  <div className="h-2 w-2 rounded-full" style={{ backgroundColor: d.fill }} />
                  <span className="text-muted-foreground">{d.name}</span>
                </div>
                <span className="font-medium tabular-nums text-foreground">{d.value}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Past Work View */}
      <PastWorkTable stats={stats} />
    </div>
  )
}

function PastWorkTable({ stats }: { stats: TaskStats | null }) {
  const [view, setView] = useState<"daily" | "weekly" | "monthly">("daily")

  const data = stats?.[view] ?? []

  const headers = {
    daily: "Date",
    weekly: "Week of",
    monthly: "Month",
  }

  return (
    <div className="rounded-2xl border border-border/50 bg-card overflow-hidden">
      <div className="flex items-center justify-between px-5 py-4 border-b border-border/50">
        <div className="flex items-center gap-2">
          <Clock className="h-4 w-4 text-muted-foreground" />
          <h3 className="font-semibold text-sm">Past Work</h3>
        </div>
        <Tabs value={view} onValueChange={(v) => setView(v as typeof view)}>
          <TabsList className="h-7 text-xs">
            <TabsTrigger value="daily" className="text-xs px-2.5">Daily</TabsTrigger>
            <TabsTrigger value="weekly" className="text-xs px-2.5">Weekly</TabsTrigger>
            <TabsTrigger value="monthly" className="text-xs px-2.5">Monthly</TabsTrigger>
          </TabsList>
        </Tabs>
      </div>

      {data.length === 0 ? (
        <div className="flex h-24 items-center justify-center text-sm text-muted-foreground">
          No data for this period
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border/30">
                <th className="px-5 py-2.5 text-left text-xs font-medium text-muted-foreground">
                  {headers[view]}
                </th>
                <th className="px-5 py-2.5 text-right text-xs font-medium text-muted-foreground">
                  Tasks Completed
                </th>
                <th className="px-5 py-2.5 text-right text-xs font-medium text-muted-foreground">
                  Progress
                </th>
              </tr>
            </thead>
            <tbody>
              {[...data].reverse().map((row) => {
                const maxCount = Math.max(...data.map((r) => r.count), 1)
                const pct = Math.round((row.count / maxCount) * 100)
                return (
                  <tr key={row.date} className="border-b border-border/20 hover:bg-muted/20 transition-colors">
                    <td className="px-5 py-3 text-foreground font-medium">
                      {formatDateLabel(row.date, view)}
                    </td>
                    <td className="px-5 py-3 text-right tabular-nums text-foreground">
                      {row.count}
                    </td>
                    <td className="px-5 py-3">
                      <div className="flex items-center gap-2 justify-end">
                        <div className="w-24 h-1.5 rounded-full bg-muted overflow-hidden">
                          <div
                            className="h-full rounded-full bg-emerald-500"
                            style={{ width: `${pct}%` }}
                          />
                        </div>
                        <span className="text-xs text-muted-foreground w-8 text-right">
                          {pct}%
                        </span>
                      </div>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
