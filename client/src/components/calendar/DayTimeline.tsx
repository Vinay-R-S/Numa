"use client"

import { useCallback, useEffect, useMemo, useRef, useState } from "react"
import { CalendarDays, Droplets, UtensilsCrossed, Clock } from "lucide-react"
import { cn } from "@/lib/utils"
import { CalendarEvent } from "@/components/calendar/api"
import { fetchTasks } from "@/components/tasklist/api"
import type { Task } from "@/components/tasklist/types"

// ── Types ────────────────────────────────────────────────────────────────────

type TimelineItemType = "calendar" | "task" | "meal" | "water"
type TimelineItemState = "upcoming" | "active" | "completed"

interface TimelineItem {
  id: string
  type: TimelineItemType
  title: string
  time: string // HH:MM
  endTime?: string
  description?: string
  state: TimelineItemState
}

export interface DayTimelineProps {
  calendarEvents: Array<{
    id: string
    title: string
    date: Date
    startTime: string
    endTime: string
    description: string
  }>
  updateIntervalMs?: number
  waterConfig?: { startHour: number; endHour: number; stepMinutes: number }
  mealTimes?: { breakfast: string; lunch: string; dinner: string }
}

// ── Helpers ──────────────────────────────────────────────────────────────────

const DOT_COLORS: Record<TimelineItemType, string> = {
  calendar: "bg-sky-400/70",
  task: "bg-blue-400/70",
  meal: "bg-amber-400/70",
  water: "bg-cyan-400/70",
}

const RING_COLORS: Record<TimelineItemType, string> = {
  calendar: "ring-sky-400/40",
  task: "ring-blue-400/40",
  meal: "ring-amber-400/40",
  water: "ring-cyan-400/40",
}

function timeToMinutes(t: string): number {
  const [h, m] = t.split(":").map(Number)
  return h * 60 + (m || 0)
}

function formatTime12(t: string): string {
  const [h, m] = t.split(":").map(Number)
  const period = h >= 12 ? "PM" : "AM"
  const display = h % 12 || 12
  return `${display}:${String(m).padStart(2, "0")} ${period}`
}

function nowHHMM(): string {
  const d = new Date()
  return `${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`
}

function computeState(time: string, endTime: string | undefined, nowStr: string): TimelineItemState {
  const nowMin = timeToMinutes(nowStr)
  const startMin = timeToMinutes(time)
  const endMin = endTime ? timeToMinutes(endTime) : startMin + 15

  if (nowMin >= endMin) return "completed"
  if (nowMin >= startMin) return "active"
  return "upcoming"
}

// ── Component ────────────────────────────────────────────────────────────────

export default function DayTimeline({
  calendarEvents,
  updateIntervalMs = 300_000,
  waterConfig,
  mealTimes,
}: DayTimelineProps) {
  const [now, setNow] = useState(nowHHMM)
  const [tasks, setTasks] = useState<Task[]>([])
  const notifiedRef = useRef(new Set<string>())

  // Request notification permission on mount
  useEffect(() => {
    if (typeof Notification !== "undefined" && Notification.permission === "default") {
      Notification.requestPermission()
    }
  }, [])

  // Live clock tick
  useEffect(() => {
    const id = window.setInterval(() => setNow(nowHHMM()), updateIntervalMs)
    return () => window.clearInterval(id)
  }, [updateIntervalMs])

  // Fetch tasks once on mount
  useEffect(() => {
    fetchTasks()
      .then((data) => setTasks(data))
      .catch(() => setTasks([]))
  }, [])

  // ── Build water reminders ──────────────────────────────────────────────

  const waterItems = useMemo((): TimelineItem[] => {
    const cfg = waterConfig ?? { startHour: 8, endHour: 22, stepMinutes: 60 }
    const items: TimelineItem[] = []
    for (let m = cfg.startHour * 60; m <= cfg.endHour * 60; m += cfg.stepMinutes) {
      const h = Math.floor(m / 60)
      const min = m % 60
      const time = `${String(h).padStart(2, "0")}:${String(min).padStart(2, "0")}`
      items.push({
        id: `water-${time}`,
        type: "water",
        title: "Drink Water",
        time,
        description: "Stay hydrated!",
        state: "upcoming",
      })
    }
    return items
  }, [waterConfig])

  // ── Build meal items ───────────────────────────────────────────────────

  const mealItems = useMemo((): TimelineItem[] => {
    const mt = mealTimes ?? { breakfast: "08:00", lunch: "13:00", dinner: "20:00" }
    return [
      { id: "meal-breakfast", type: "meal" as const, title: "Breakfast", time: mt.breakfast, description: "Time for breakfast", state: "upcoming" as const },
      { id: "meal-lunch", type: "meal" as const, title: "Lunch", time: mt.lunch, description: "Lunch break", state: "upcoming" as const },
      { id: "meal-dinner", type: "meal" as const, title: "Dinner", time: mt.dinner, description: "Dinner time", state: "upcoming" as const },
    ]
  }, [mealTimes])

  // ── Build task items (only today's tasks with due_date or reminder_at) ─

  const taskItems = useMemo((): TimelineItem[] => {
    const todayStr = new Date().toISOString().slice(0, 10)
    return tasks
      .filter((t) => {
        const due = t.due_date?.slice(0, 10)
        return due === todayStr && t.status !== "completed"
      })
      .map((t) => {
        const time = t.reminder_at
          ? new Date(t.reminder_at).toTimeString().slice(0, 5)
          : "09:00"
        return {
          id: `task-${t.id}`,
          type: "task" as const,
          title: t.title,
          time,
          description: t.description ?? undefined,
          state: "upcoming" as const,
        }
      })
  }, [tasks])

  // ── Build calendar items ───────────────────────────────────────────────

  const calendarItems = useMemo((): TimelineItem[] => {
    return calendarEvents.map((e) => ({
      id: `cal-${e.id}`,
      type: "calendar" as const,
      title: e.title,
      time: e.startTime,
      endTime: e.endTime,
      description: e.description,
      state: "upcoming" as const,
    }))
  }, [calendarEvents])

  // ── Merge & sort all items ─────────────────────────────────────────────

  const allItems = useMemo(() => {
    const merged = [...calendarItems, ...taskItems, ...mealItems, ...waterItems]
    merged.sort((a, b) => timeToMinutes(a.time) - timeToMinutes(b.time))
    return merged.map((item) => ({
      ...item,
      state: computeState(item.time, item.endTime, now),
    }))
  }, [calendarItems, taskItems, mealItems, waterItems, now])

  // ── Send browser notifications on state becoming active ────────────────

  const fireNotification = useCallback((item: TimelineItem) => {
    if (notifiedRef.current.has(item.id)) return
    notifiedRef.current.add(item.id)

    if (typeof Notification !== "undefined" && Notification.permission === "granted") {
      new Notification(`NUMA Timeline`, { body: item.title, icon: "/favicon.ico" })
    }
  }, [])

  useEffect(() => {
    allItems.forEach((item) => {
      if (item.state === "active") {
        fireNotification(item)
      }
    })
  }, [allItems, fireNotification])

  // ── Compute progress position (percentage through today 6AM-11PM) ──────

  const progressPct = useMemo(() => {
    const nowMin = timeToMinutes(now)
    const dayStart = 6 * 60
    const dayEnd = 23 * 60
    return Math.max(0, Math.min(100, ((nowMin - dayStart) / (dayEnd - dayStart)) * 100))
  }, [now])

  const today = new Date()
  const dateLabel = today.toLocaleDateString("en-US", {
    weekday: "long",
    month: "short",
    day: "numeric",
  })

  const totalEvents = allItems.length
  const completedCount = allItems.filter((i) => i.state === "completed").length

  return (
    <div className="flex h-full flex-col overflow-hidden rounded-xl border border-border/40 bg-card/40">
      {/* Header */}
      <div className="shrink-0 border-b border-border/30 px-4 py-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <CalendarDays className="h-4 w-4 text-primary" />
            <h3 className="text-sm font-semibold text-foreground">Today</h3>
          </div>
          <span className="rounded-full bg-primary/10 px-2 py-0.5 text-[10px] font-medium text-primary">
            {completedCount}/{totalEvents}
          </span>
        </div>
        <p className="mt-0.5 text-[11px] text-muted-foreground">{dateLabel}</p>
      </div>

      {/* Timeline body */}
      <div className="relative min-h-0 flex-1 overflow-y-auto py-3">
        {/* Current-time indicator */}
        <div
          className="absolute left-[11px] z-10 transition-all duration-1000"
          style={{ top: `calc(${progressPct}%)` }}
        >
          <div className="h-3.5 w-3.5 rounded-full bg-primary border-2 border-card" />
        </div>

        {/* Event items */}
        {allItems.map((item) => (
          <div key={item.id} className={cn(
            "relative flex items-start py-2 pl-10 pr-4",
            item.state === "completed" && "opacity-50",
            item.state === "active" && "bg-primary/5 rounded-lg"
          )}>
            {/* Vertical line segment */}
            <div className="absolute left-[18px] top-0 bottom-0 w-px bg-border/30" />

            {/* Dot centered on the line */}
            <div className={cn(
              "absolute left-[14px] top-3 h-2.5 w-2.5 rounded-full",
              DOT_COLORS[item.type],
              item.state === "active" && "h-3 w-3 left-[13.5px] ring-2 animate-pulse",
              item.state === "active" && RING_COLORS[item.type],
            )} />

            {/* Content */}
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-1.5">
                <TimelineIcon type={item.type} />
                <span
                  className={cn(
                    "truncate text-xs font-medium text-foreground",
                    item.state === "completed" && "line-through text-muted-foreground"
                  )}
                >
                  {item.title}
                </span>
              </div>

              <div className="mt-0.5 flex items-center gap-1 text-[10px] text-muted-foreground">
                <span>{formatTime12(item.time)}</span>
                {item.endTime && (
                  <>
                    <span>-</span>
                    <span>{formatTime12(item.endTime)}</span>
                  </>
                )}
              </div>

              {item.description && (
                <p className="mt-0.5 truncate text-[10px] leading-tight text-muted-foreground/70">
                  {item.description}
                </p>
              )}
            </div>
          </div>
        ))}

        {allItems.length === 0 && (
          <p className="py-8 text-center text-xs text-muted-foreground">
            No events for today
          </p>
        )}
      </div>
    </div>
  )
}

// ── Timeline Icon ────────────────────────────────────────────────────────────

function TimelineIcon({ type }: { type: TimelineItemType }) {
  if (type === "water") return <Droplets className="h-3 w-3 text-cyan-400/80" />
  if (type === "meal") return <UtensilsCrossed className="h-3 w-3 text-amber-400/80" />
  if (type === "task") return <Clock className="h-3 w-3 text-blue-400/80" />
  return null
}
