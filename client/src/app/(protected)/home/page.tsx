"use client"

import { Button } from "@/components/ui/button"
import {
  DashboardHeader,
  DeveloperCard,
  HealthSection,
  MasterAgentPanel,
  OverviewRow,
  RecentTasksCard,
  STAT_SKELETON_KEYS,
  StatCardSkeleton,
  TaskDistributionChart,
  TaskStatsRow,
  UpcomingEventsCard,
  WeeklyActivityChart,
  useDashboard,
  useMasterAgentChat,
} from "@/features/dashboard"

export default function HomePage() {
  const {
    user,
    stats,
    tasks,
    todayTasks,
    health,
    upcomingEvents,
    initialLoading,
    syncingAll,
    refreshingStats,
    refreshStatsSilently,
    handleRefreshStats,
    handleFetchLatest,
  } = useDashboard()

  const chat = useMasterAgentChat({ onDataChanged: refreshStatsSilently })

  const renderBody = () => {
    if (initialLoading) {
      return (
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
            {STAT_SKELETON_KEYS.map((key) => (
              <StatCardSkeleton key={key} />
            ))}
          </div>
        </div>
      )
    }

    if (!stats) {
      return (
        <div className="text-center py-16 text-muted-foreground">
          <p>Could not load dashboard data</p>
          <Button variant="outline" size="sm" className="mt-3" onClick={refreshStatsSilently}>
            Retry
          </Button>
        </div>
      )
    }

    return (
      <>
        <TaskStatsRow tasks={tasks} />

        <TaskDistributionChart
          completed={todayTasks.completed}
          inprogress={todayTasks.inprogress ?? 0}
          pending={todayTasks.pending}
        />

        <OverviewRow
          calendar={stats.calendar}
          slack={stats.slack}
          journal={stats.journal}
          upcomingCount={upcomingEvents.length}
        />

        <HealthSection health={health} />

        <WeeklyActivityChart data={stats.health_weekly ?? []} />

        <div className="grid gap-3 sm:grid-cols-2">
          <UpcomingEventsCard events={upcomingEvents} />
          <DeveloperCard github={stats.github} />
        </div>

        <RecentTasksCard tasks={tasks.recent} />
      </>
    )
  }

  return (
    <div className="h-full w-full overflow-y-auto px-4 py-5 sm:px-6 sm:py-6">
      <div className="space-y-5">
        <DashboardHeader
          user={user}
          hasStats={Boolean(stats)}
          initialLoading={initialLoading}
          syncingAll={syncingAll}
          refreshingStats={refreshingStats}
          agentOpen={chat.open}
          onSyncAll={() => void handleFetchLatest()}
          onRefresh={() => void handleRefreshStats()}
          onToggleAgent={chat.toggle}
        />

        {renderBody()}
      </div>

      {chat.open && (
        <MasterAgentPanel
          messages={chat.messages}
          input={chat.input}
          sending={chat.sending}
          chatError={chat.chatError}
          lastDelegation={chat.lastDelegation}
          canSend={chat.canSend}
          chatEndRef={chat.chatEndRef}
          setInput={chat.setInput}
          close={chat.close}
          handleSend={chat.handleSend}
          handleStop={chat.handleStop}
        />
      )}
    </div>
  )
}
