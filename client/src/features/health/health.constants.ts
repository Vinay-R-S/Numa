/**
 * Health feature constants (NUMA-116 P4, PLAN 17.2).
 *
 * Values lifted verbatim from `health/page.tsx`: the chart metric options, the
 * sleep stage palette, the goals each card renders against and the agent dock
 * copy. The metric/heart card lists were hand-written JSX in the page and are
 * data here, so the grids render from one source without changing what shows.
 */
import type { ElementType } from "react"
import { Activity, Flame, Footprints, Heart, HeartPulse, MapPin, Moon } from "lucide-react"

import type { HealthAgentMessage, SleepStage, WeeklyActivityMetric } from "./health.types"

/** Snapshot window the page loads: 7 rolling days plus today. */
export const SNAPSHOT_DAYS = 8

export const DAY_NAMES = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]

export const SLEEP_GOAL_HOURS = 8

export interface WeeklyActivityOption {
  key: WeeklyActivityMetric
  label: string
  unit: string
  color: string
  icon: ElementType
}

export const WEEKLY_ACTIVITY_OPTIONS: WeeklyActivityOption[] = [
  { key: "steps", label: "Steps", unit: "steps", color: "#22d3ee", icon: Footprints },
  { key: "calories", label: "Calories", unit: "kcal", color: "#fb923c", icon: Flame },
  { key: "distance_km", label: "Distance", unit: "km", color: "#c084fc", icon: MapPin },
]

export const SLEEP_STAGE_META: Record<
  SleepStage,
  { label: string; fill: string; dot: string; priority: number }
> = {
  deep: { label: "Deep", fill: "bg-indigo-500", dot: "bg-indigo-500", priority: 4 },
  rem: { label: "REM", fill: "bg-purple-500", dot: "bg-purple-500", priority: 3 },
  light: { label: "Light", fill: "bg-blue-500", dot: "bg-blue-500", priority: 2 },
  generic: { label: "Asleep", fill: "bg-slate-500", dot: "bg-slate-500", priority: 1 },
}

/** Stage order of the summary tiles under the sleep timeline. */
export const SLEEP_STAGE_ORDER: SleepStage[] = ["deep", "rem", "light", "generic"]

/** Numeric snapshot fields the five progress cards read. */
export type MetricKey = "steps" | "active_minutes" | "calories" | "distance_km" | "sleep_hours"

export interface MetricCardConfig {
  key: MetricKey
  label: string
  unit: string
  goal: number
  color: string
  icon: ElementType
}

export const METRIC_CARDS: MetricCardConfig[] = [
  { key: "steps", label: "Steps", unit: "steps", goal: 10000, color: "bg-cyan-500/80", icon: Footprints },
  { key: "active_minutes", label: "Active Minutes", unit: "min", goal: 60, color: "bg-emerald-500/80", icon: Activity },
  { key: "calories", label: "Calories", unit: "kcal", goal: 2500, color: "bg-orange-500/80", icon: Flame },
  { key: "distance_km", label: "Distance", unit: "km", goal: 8, color: "bg-purple-500/80", icon: MapPin },
  { key: "sleep_hours", label: "Sleep", unit: "hrs", goal: SLEEP_GOAL_HOURS, color: "bg-indigo-500/80", icon: Moon },
]

export interface HeartMetricConfig {
  key: "heart_rate_bpm" | "heart_points"
  label: string
  unit: string
  goal: number
  helper: string
  icon: ElementType
  accent: { text: string; stroke: string; bg: string; ring: string }
}

export const HEART_METRIC_CARDS: HeartMetricConfig[] = [
  {
    key: "heart_rate_bpm",
    label: "Heart Rate",
    unit: "bpm",
    goal: 120,
    helper: "Daily average from Google Fit",
    icon: HeartPulse,
    accent: {
      text: "text-rose-400",
      stroke: "text-rose-400",
      bg: "bg-rose-500/10",
      ring: "ring-1 ring-rose-500/20",
    },
  },
  {
    key: "heart_points",
    label: "Heart Points",
    unit: "pts",
    goal: 30,
    helper: "Move minutes with higher intensity",
    icon: Heart,
    accent: {
      text: "text-pink-400",
      stroke: "text-pink-400",
      bg: "bg-pink-500/10",
      ring: "ring-1 ring-pink-500/20",
    },
  },
]

export const HEALTH_AGENT_SESSION_KEY = "numa:session:health-agent-chat"

export const HEALTH_AGENT_GREETING: HealthAgentMessage[] = [
  {
    role: "assistant",
    content:
      "Hi! I'm your NUMA Health agent. I can show your fitness data, weekly trends, and personalized insights from Google Fit and Strava. What would you like to know?",
  },
]

export const HEALTH_AGENT_SUGGESTIONS = [
  "How am I doing today?",
  "Show weekly trends",
  "Recommend a diet plan",
  "Suggest yoga for me",
  "Give me insights",
]
