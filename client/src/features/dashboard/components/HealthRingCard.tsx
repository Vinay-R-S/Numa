"use client"

import React from "react"
import { cn } from "@/lib/utils"

const RADIUS = 28
const CIRCUMFERENCE = 2 * Math.PI * RADIUS

interface HealthRingCardProps {
  icon: React.ElementType
  label: string
  value: number
  unit: string
  goal: number
  iconColor: string
  ringColor: string
  className?: string
  featured?: boolean
}

export function HealthRingCard({
  icon: Icon,
  label,
  value,
  unit,
  goal,
  iconColor,
  ringColor,
  className,
  featured = false,
}: HealthRingCardProps) {
  const pct = Math.min(value / goal, 1)
  const offset = CIRCUMFERENCE * (1 - pct)

  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center gap-2 rounded-xl border border-border/40 bg-card/40 p-4",
        featured ? "min-h-[220px] sm:min-h-[248px]" : "min-h-[118px]",
        className
      )}
    >
      <div className={cn("relative", featured ? "h-24 w-24" : "h-20 w-20")}>
        <svg viewBox="0 0 64 64" className="h-full w-full -rotate-90">
          <circle cx="32" cy="32" r={RADIUS} fill="none" strokeWidth="5" className="stroke-muted/30" />
          <circle
            cx="32"
            cy="32"
            r={RADIUS}
            fill="none"
            strokeWidth="5"
            strokeLinecap="round"
            className={ringColor}
            strokeDasharray={CIRCUMFERENCE}
            strokeDashoffset={offset}
            style={{ transition: "stroke-dashoffset 0.6s ease" }}
          />
        </svg>
        <div className="absolute inset-0 flex items-center justify-center">
          <Icon className={cn(featured ? "h-6 w-6" : "h-5 w-5", iconColor)} />
        </div>
      </div>
      <div className="text-center">
        <div className="flex items-baseline justify-center gap-1">
          <span
            className={cn(
              "font-bold text-foreground tabular-nums",
              featured ? "text-2xl" : "text-lg"
            )}
          >
            {value % 1 !== 0 ? value.toFixed(1) : value.toLocaleString()}
          </span>
          <span className={cn("text-muted-foreground", featured ? "text-sm" : "text-xs")}>{unit}</span>
        </div>
        <p className={cn("font-medium text-muted-foreground", featured ? "text-sm" : "text-xs")}>
          {label}
        </p>
        <p className={cn("text-muted-foreground/60", featured ? "text-xs" : "text-[11px]")}>
          {Math.round(pct * 100)}% of {goal.toLocaleString()}
        </p>
      </div>
    </div>
  )
}
