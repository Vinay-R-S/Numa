"use client"

import { AlertCircle, CheckSquare, Flame, ListTodo, TrendingUp } from "lucide-react"
import { ICON_COLORS } from "../dashboard.constants"
import type { DashboardTasks } from "../dashboard.types"
import { StatCard } from "./StatCard"

export function TaskStatsRow({ tasks }: { tasks: DashboardTasks }) {
  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
      <StatCard icon={ListTodo} label="Total Tasks" value={tasks.total} sub="all time" href="/tasklist" iconColor={ICON_COLORS.tasks} />
      <StatCard icon={CheckSquare} label="Completed" value={tasks.completed} sub="done" href="/tasklist" iconColor={ICON_COLORS.completed} />
      <StatCard icon={TrendingUp} label="In Progress" value={tasks.inprogress ?? 0} sub="active" href="/tasklist" iconColor={ICON_COLORS.inprogress} />
      <StatCard icon={AlertCircle} label="Pending" value={tasks.pending} sub="blocked" href="/tasklist" iconColor={ICON_COLORS.pending} />
      <StatCard icon={Flame} label="Current Streak" value={`${tasks.streak ?? 0}d`} sub="consecutive days" iconColor={ICON_COLORS.streak} />
    </div>
  )
}
