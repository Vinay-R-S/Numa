"use client"

import type { ElementType } from "react"

import { formatNumber, pct } from "../health.utils"

interface HeartMetricCardProps {
  icon: ElementType
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
}

export function HeartMetricCard({
  icon: Icon,
  label,
  value,
  unit,
  goal,
  helper,
  accent,
}: HeartMetricCardProps) {
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
