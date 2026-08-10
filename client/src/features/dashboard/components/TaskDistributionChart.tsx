"use client"

import { Bar, BarChart, CartesianGrid, Cell, XAxis, YAxis } from "recharts"
import { Zap } from "lucide-react"
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from "@/components/ui/chart"
import { cn } from "@/lib/utils"
import { ICON_COLORS } from "../dashboard.constants"

const CHART_CONFIG = {
  value: { label: "Tasks" },
} satisfies ChartConfig

interface TaskDistributionChartProps {
  completed: number
  inprogress: number
  pending: number
}

export function TaskDistributionChart({
  completed,
  inprogress,
  pending,
}: TaskDistributionChartProps) {
  const total = completed + inprogress + pending
  const donePct = total > 0 ? Math.round((completed / total) * 100) : 0
  const items = [
    { label: "Completed", value: completed, fill: "#34d399" },
    { label: "In Progress", value: inprogress, fill: "#fbbf24" },
    { label: "Pending", value: pending, fill: "#fb7185" },
  ]
  const maxTaskValue = Math.max(...items.map((item) => item.value), 1)

  return (
    <div className="rounded-xl border border-border/40 bg-card/40 p-4 sm:p-5">
      <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-2">
          <Zap className={cn("h-4 w-4", ICON_COLORS.tasks)} />
          <div>
            <span className="text-sm font-semibold text-foreground">Task Distribution</span>
            <p className="text-[10px] text-muted-foreground">Today&apos;s tasks only</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <div className="rounded-lg border border-border/30 bg-background/30 px-3 py-1.5">
            <p className="text-[10px] font-medium uppercase text-muted-foreground/70">Total</p>
            <p className="text-sm font-bold text-foreground tabular-nums">{total}</p>
          </div>
          <div className="rounded-lg border border-border/30 bg-background/30 px-3 py-1.5">
            <p className="text-[10px] font-medium uppercase text-muted-foreground/70">Done</p>
            <p className="text-sm font-bold text-foreground tabular-nums">{donePct}%</p>
          </div>
        </div>
      </div>

      <ChartContainer config={CHART_CONFIG} className="h-48 w-full">
        <BarChart data={items} layout="vertical" margin={{ left: 8, right: 20, top: 4, bottom: 4 }}>
          <CartesianGrid horizontal={false} strokeDasharray="4 4" />
          <XAxis type="number" hide domain={[0, maxTaskValue]} />
          <YAxis type="category" dataKey="label" width={86} tickLine={false} axisLine={false} fontSize={12} />
          <ChartTooltip
            cursor={{ fill: "hsl(var(--muted) / 0.18)" }}
            content={<ChartTooltipContent hideLabel formatter={(value) => `${value} tasks`} />}
          />
          <Bar dataKey="value" radius={[0, 8, 8, 0]} barSize={26}>
            {items.map((item) => (
              <Cell key={item.label} fill={item.fill} />
            ))}
          </Bar>
        </BarChart>
      </ChartContainer>

      <div className="mt-3 flex flex-wrap items-center justify-center gap-4">
        {items.map((item) => (
          <div key={item.label} className="flex items-center gap-1.5">
            <div className="h-2 w-2 rounded-full" style={{ backgroundColor: item.fill }} />
            <span className="text-[10px] text-muted-foreground">
              {item.label}: {item.value}
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}
