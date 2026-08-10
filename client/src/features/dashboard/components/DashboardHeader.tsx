"use client"

import { RefreshCw, Sparkles } from "lucide-react"
import { HeaderActionButton } from "@/components/ui/header-action-button"
import { LiveDataPill } from "@/components/ui/live-data-pill"
import type { DashboardUser } from "../dashboard.types"

interface DashboardHeaderProps {
  user: DashboardUser | null
  hasStats: boolean
  initialLoading: boolean
  syncingAll: boolean
  refreshingStats: boolean
  agentOpen: boolean
  onSyncAll: () => void
  onRefresh: () => void
  onToggleAgent: () => void
}

export function DashboardHeader({
  user,
  hasStats,
  initialLoading,
  syncingAll,
  refreshingStats,
  agentOpen,
  onSyncAll,
  onRefresh,
  onToggleAgent,
}: DashboardHeaderProps) {
  const displayName = user ? user.full_name || user.email.split("@")[0] : null

  return (
    <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
      <div>
        <h1 className="text-xl font-bold tracking-tight text-foreground sm:text-2xl">
          {displayName ? `Welcome, ${displayName}` : "Dashboard"}
        </h1>
        <p className="text-xs text-muted-foreground sm:text-sm">Your NUMA overview for today</p>
      </div>
      <div className="flex items-center gap-2">
        <LiveDataPill live={hasStats} loading={initialLoading} />
        <HeaderActionButton
          icon={RefreshCw}
          label="Sync All"
          loading={syncingAll}
          active={syncingAll}
          onClick={onSyncAll}
          disabled={syncingAll}
        >
          {syncingAll ? "Syncing..." : "Sync All"}
        </HeaderActionButton>
        <HeaderActionButton
          icon={RefreshCw}
          label="Refresh"
          loading={refreshingStats || initialLoading}
          active={refreshingStats}
          onClick={onRefresh}
          disabled={refreshingStats || initialLoading}
        />
        <HeaderActionButton icon={Sparkles} label="Agent" active={agentOpen} onClick={onToggleAgent} />
      </div>
    </div>
  )
}
