"use client"

import { Heart } from "lucide-react"

import type { HealthSnapshot } from "../health.types"

/** Four equally weighted goals: 10k steps, 60 active minutes, 2500 kcal, 8h sleep. */
function computeScore(snapshot: HealthSnapshot | null): number {
  const steps = snapshot?.steps || 0
  const active = snapshot?.active_minutes || 0
  const calories = snapshot?.calories || 0
  const sleep = snapshot?.sleep_hours || 0

  return Math.round(
    Math.min(steps / 10000, 1) * 25 +
    Math.min(active / 60, 1) * 25 +
    Math.min(calories / 2500, 1) * 25 +
    Math.min(sleep / 8, 1) * 25
  )
}

function scoreTheme(score: number) {
  if (score >= 75) {
    return {
      level: "Excellent",
      color: "text-emerald-400",
      ring: "text-emerald-500",
      badge: "border-emerald-500/20 bg-emerald-500/10 text-emerald-400",
      bar: "from-emerald-500 to-green-400",
    }
  }
  if (score >= 50) {
    return {
      level: "Good",
      color: "text-yellow-400",
      ring: "text-yellow-500",
      badge: "border-yellow-500/20 bg-yellow-500/10 text-yellow-400",
      bar: "from-yellow-500 to-amber-400",
    }
  }
  if (score >= 25) {
    return {
      level: "Fair",
      color: "text-orange-400",
      ring: "text-orange-500",
      badge: "border-orange-500/20 bg-orange-500/10 text-orange-400",
      bar: "from-orange-500 to-red-400",
    }
  }
  return {
    level: "Needs Work",
    color: "text-red-400",
    ring: "text-red-500",
    badge: "border-orange-500/20 bg-orange-500/10 text-orange-400",
    bar: "from-orange-500 to-red-400",
  }
}

export function HealthScore({ snapshot }: { snapshot: HealthSnapshot | null }) {
  const score = computeScore(snapshot)
  const theme = scoreTheme(score)

  return (
    <div className="rounded-2xl border border-border/40 bg-card/40 p-4 sm:p-6">
      <div className="flex flex-col items-center gap-4 sm:flex-row sm:items-center sm:gap-5">
        {/* Score ring */}
        <div className="relative shrink-0">
          <svg width={80} height={80} viewBox="0 0 100 100" className="sm:h-[100px] sm:w-[100px]" style={{ transform: "rotate(-90deg)" }}>
            <circle cx={50} cy={50} r={42} fill="none" stroke="currentColor" strokeWidth={8} className="text-border/20" />
            <circle cx={50} cy={50} r={42} fill="none" stroke="currentColor" strokeWidth={8}
              className={theme.ring} strokeLinecap="round"
              strokeDasharray={2 * Math.PI * 42}
              strokeDashoffset={2 * Math.PI * 42 * (1 - score / 100)}
              style={{ transition: "stroke-dashoffset 1.2s ease-out" }} />
          </svg>
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <span className={`text-3xl font-black tabular-nums ${theme.color}`}>{score}</span>
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
          <div className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-bold ${theme.badge}`}>
            {theme.level}
          </div>

          <div className="mt-3 w-full h-2 bg-border/20 rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full transition-all bg-linear-to-r ${theme.bar}`}
              style={{ width: `${score}%` }}
            />
          </div>
        </div>
      </div>
    </div>
  )
}
