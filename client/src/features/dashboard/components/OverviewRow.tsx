"use client"

import { BookOpen, CalendarDays, Slack } from "lucide-react"
import { ICON_COLORS } from "../dashboard.constants"
import type { DashboardCalendar, DashboardJournal, DashboardSlack } from "../dashboard.types"
import { StatCard } from "./StatCard"

interface OverviewRowProps {
  calendar: DashboardCalendar
  slack: DashboardSlack
  journal: DashboardJournal
  upcomingCount: number
}

export function OverviewRow({ calendar, slack, journal, upcomingCount }: OverviewRowProps) {
  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
      <StatCard
        icon={CalendarDays}
        label="Events Today"
        value={calendar.today_events}
        sub={`${upcomingCount} upcoming`}
        href="/calendar"
        iconColor={ICON_COLORS.calendar}
      />
      <StatCard
        icon={Slack}
        label="Slack Messages"
        value={slack.messages_7d}
        sub={`${slack.active_channels} channels (7d)`}
        href="/slack"
        iconColor={ICON_COLORS.slack}
      />
      <StatCard
        icon={BookOpen}
        label="Journal Streak"
        value={`${journal.streak}d`}
        sub={journal.today_mood ? `Today: ${journal.today_mood}` : "No entry yet"}
        href="/journal"
        iconColor={ICON_COLORS.journal}
      />
    </div>
  )
}
