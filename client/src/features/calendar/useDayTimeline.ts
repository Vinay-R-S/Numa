/**
 * Day timeline hook (NUMA-114 P4, PLAN 21.2).
 *
 * Builds today's merged timeline (calendar events + due tasks + meal and water
 * reminders), keeps the live clock ticking and fires the browser notification
 * when an item becomes active. `DayTimeline` only renders the rows.
 */
import { useCallback, useEffect, useMemo, useRef, useState } from "react"

import { fetchTasks } from "@/features/tasks/tasks.api"
import type { Task } from "@/features/tasks/tasks.types"
import {
  DEFAULT_MEAL_TIMES,
  DEFAULT_TIMELINE_INTERVAL_MS,
  DEFAULT_WATER_CONFIG,
} from "./calendar.constants"
import { minutesToTime, nowHHMM, timeToMinutes, timelineItemState, toDateParam } from "./calendar.utils"
import type { CalendarEvent, TimelineItem, TimelineSettings } from "./calendar.types"

interface UseDayTimelineOptions {
  calendarEvents: CalendarEvent[]
  updateIntervalMs?: number
  waterConfig?: TimelineSettings["waterConfig"]
  mealTimes?: TimelineSettings["mealTimes"]
}

export type TimelineRowModel =
  | { kind: "item"; item: TimelineItem; time: string }
  | { kind: "now"; time: string }

export function useDayTimeline({
  calendarEvents,
  updateIntervalMs = DEFAULT_TIMELINE_INTERVAL_MS,
  waterConfig,
  mealTimes,
}: UseDayTimelineOptions) {
  const [now, setNow] = useState("00:00")
  const [dateLabel, setDateLabel] = useState("")
  const [tasks, setTasks] = useState<Task[]>([])
  const notifiedRef = useRef(new Set<string>())

  useEffect(() => {
    if (typeof Notification !== "undefined" && Notification.permission === "default") {
      Notification.requestPermission()
    }
  }, [])

  // Clock starts after hydration so server and client markup match.
  useEffect(() => {
    const hydrationId = globalThis.setTimeout(() => setNow(nowHHMM()), 0)
    const tickId = globalThis.setInterval(() => setNow(nowHHMM()), updateIntervalMs)
    return () => {
      globalThis.clearTimeout(hydrationId)
      globalThis.clearInterval(tickId)
    }
  }, [updateIntervalMs])

  useEffect(() => {
    const id = globalThis.setTimeout(() => {
      setDateLabel(
        new Date().toLocaleDateString("en-US", { weekday: "long", month: "short", day: "numeric" })
      )
    }, 0)
    return () => globalThis.clearTimeout(id)
  }, [])

  useEffect(() => {
    fetchTasks()
      .then(setTasks)
      .catch(() => setTasks([]))
  }, [])

  const waterItems = useMemo((): TimelineItem[] => {
    const config = waterConfig ?? DEFAULT_WATER_CONFIG
    const items: TimelineItem[] = []

    for (
      let minutes = config.startHour * 60;
      minutes <= config.endHour * 60;
      minutes += config.stepMinutes
    ) {
      const time = minutesToTime(minutes)
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

  const mealItems = useMemo((): TimelineItem[] => {
    const times = mealTimes ?? DEFAULT_MEAL_TIMES
    return [
      { id: "meal-breakfast", type: "meal", title: "Breakfast", time: times.breakfast, description: "Time for breakfast", state: "upcoming" },
      { id: "meal-lunch", type: "meal", title: "Lunch", time: times.lunch, description: "Lunch break", state: "upcoming" },
      { id: "meal-dinner", type: "meal", title: "Dinner", time: times.dinner, description: "Dinner time", state: "upcoming" },
    ]
  }, [mealTimes])

  const taskItems = useMemo((): TimelineItem[] => {
    const todayStr = toDateParam(new Date())

    return tasks
      .filter((task) => task.due_date?.slice(0, 10) === todayStr && task.status !== "completed")
      .map((task) => ({
        id: `task-${task.id}`,
        type: "task",
        title: task.title,
        time: task.reminder_at ? new Date(task.reminder_at).toTimeString().slice(0, 5) : "09:00",
        description: task.description ?? undefined,
        state: "upcoming",
      }))
  }, [tasks])

  const calendarItems = useMemo((): TimelineItem[] => {
    return calendarEvents.map((event) => ({
      id: `cal-${event.id}`,
      type: "calendar",
      title: event.title,
      time: event.startTime,
      endTime: event.endTime,
      description: event.description,
      state: "upcoming",
    }))
  }, [calendarEvents])

  const allItems = useMemo(() => {
    const merged = [...calendarItems, ...taskItems, ...mealItems, ...waterItems]
    merged.sort((a, b) => timeToMinutes(a.time) - timeToMinutes(b.time))
    return merged.map((item) => ({ ...item, state: timelineItemState(item.time, item.endTime, now) }))
  }, [calendarItems, taskItems, mealItems, waterItems, now])

  const rows = useMemo((): TimelineRowModel[] => {
    return [
      ...allItems.map((item) => ({ kind: "item" as const, item, time: item.time })),
      { kind: "now" as const, time: now },
    ].sort((a, b) => timeToMinutes(a.time) - timeToMinutes(b.time))
  }, [allItems, now])

  const fireNotification = useCallback((item: TimelineItem) => {
    if (notifiedRef.current.has(item.id)) return
    notifiedRef.current.add(item.id)

    if (typeof Notification !== "undefined" && Notification.permission === "granted") {
      new Notification("NUMA Timeline", { body: item.title, icon: "/favicon.ico" })
    }
  }, [])

  useEffect(() => {
    allItems.filter((item) => item.state === "active").forEach(fireNotification)
  }, [allItems, fireNotification])

  return {
    now,
    dateLabel,
    rows,
    isEmpty: allItems.length === 0,
    totalEvents: allItems.length,
    completedCount: allItems.filter((item) => item.state === "completed").length,
  }
}

export type UseDayTimelineReturn = ReturnType<typeof useDayTimeline>
