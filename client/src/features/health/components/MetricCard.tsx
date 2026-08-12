"use client"

import type { ElementType } from "react"

import { formatNumber, pct } from "../health.utils"

interface MetricCardProps {
  icon: ElementType
  label: string
  value: number | null
  unit: string
  goal: number
  color: string
}

export function MetricCard({ icon: Icon, label, value, unit, goal, color }: MetricCardProps) {
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
