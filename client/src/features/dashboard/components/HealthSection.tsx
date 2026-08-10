"use client"

import type { ElementType } from "react"
import { Activity, ArrowRight, Flame, Footprints, Heart, HeartPulse, MapPin, Moon } from "lucide-react"
import { cn } from "@/lib/utils"
import { ICON_COLORS } from "../dashboard.constants"
import type { DashboardHealth } from "../dashboard.types"
import { HealthRingCard } from "./HealthRingCard"

/** Daily goals the rings fill against, unchanged from the original page. */
const RINGS = [
  { key: "steps", icon: Footprints, label: "Steps", unit: "steps", goal: 10000, iconColor: ICON_COLORS.steps, ringColor: "stroke-cyan-400" },
  { key: "active_minutes", icon: Activity, label: "Active Minutes", unit: "min", goal: 60, iconColor: ICON_COLORS.active, ringColor: "stroke-emerald-400" },
  { key: "calories", icon: Flame, label: "Calories", unit: "kcal", goal: 2000, iconColor: ICON_COLORS.calories, ringColor: "stroke-orange-400" },
  { key: "sleep_hours", icon: Moon, label: "Sleep", unit: "hrs", goal: 8, iconColor: ICON_COLORS.sleep, ringColor: "stroke-indigo-400" },
  { key: "distance_km", icon: MapPin, label: "Distance", unit: "km", goal: 5, iconColor: ICON_COLORS.distance, ringColor: "stroke-violet-400" },
  { key: "heart_rate_bpm", icon: HeartPulse, label: "Heart Rate", unit: "bpm", goal: 120, iconColor: ICON_COLORS.heartRate, ringColor: "stroke-rose-400" },
] as const satisfies ReadonlyArray<{
  key: keyof DashboardHealth
  icon: ElementType
  label: string
  unit: string
  goal: number
  iconColor: string
  ringColor: string
}>

export function HealthSection({ health }: { health: DashboardHealth }) {
  return (
    <div className="rounded-xl border border-border/40 bg-card/40 p-4 sm:p-5">
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Heart className={cn("h-4 w-4", ICON_COLORS.health)} />
          <span className="text-sm font-semibold text-foreground">Today&apos;s Health</span>
        </div>
        <a
          href="/health"
          className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
        >
          Details <ArrowRight className="h-3 w-3" />
        </a>
      </div>
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-[repeat(3,minmax(0,1fr))_minmax(180px,0.9fr)] lg:grid-rows-2">
        {RINGS.map((ring) => (
          <HealthRingCard
            key={ring.key}
            icon={ring.icon}
            label={ring.label}
            value={health[ring.key] ?? 0}
            unit={ring.unit}
            goal={ring.goal}
            iconColor={ring.iconColor}
            ringColor={ring.ringColor}
          />
        ))}
        <HealthRingCard
          icon={Heart}
          label="Heart Points"
          value={health.heart_points ?? 0}
          unit="pts"
          goal={30}
          iconColor={ICON_COLORS.heartPoints}
          ringColor="stroke-pink-400"
          className="sm:col-span-3 lg:col-span-1 lg:col-start-4 lg:row-span-2 lg:row-start-1"
          featured
        />
      </div>
    </div>
  )
}
