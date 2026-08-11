"use client"

import { RefreshCw, Slack, Sparkles } from "lucide-react"

import { HeaderActionButton } from "@/components/ui/header-action-button"
import { LiveDataPill } from "@/components/ui/live-data-pill"
import type { SlackStatus } from "../slack.types"

interface SlackPageHeaderProps {
  status: SlackStatus | null
  syncing: boolean
  loadingMessages: boolean
  agentOpen: boolean
  onSync: () => void
  onRefresh: () => void
  onToggleAgent: () => void
}

export function SlackPageHeader({
  status,
  syncing,
  loadingMessages,
  agentOpen,
  onSync,
  onRefresh,
  onToggleAgent,
}: SlackPageHeaderProps) {
  const connected = Boolean(status?.connected)

  return (
    <header className="flex flex-col gap-3 rounded-2xl border border-border/40 bg-card/40 p-4 sm:flex-row sm:items-center sm:justify-between sm:p-5 shrink-0">
      <div className="flex items-center gap-3">
        <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-muted/30 ring-1 ring-border/50">
          <Slack className="h-5 w-5 text-foreground" />
        </div>
        <div>
          <h1 className="text-xl font-bold tracking-tight text-foreground sm:text-2xl">
            Slack Integration
          </h1>
          <p className="text-xs text-muted-foreground sm:text-sm">
            AI-powered Slack agent • 7-day rolling message window
          </p>
        </div>
      </div>

      <div className="flex items-center gap-2">
        <LiveDataPill live={connected} loading={!status} configured={connected} />
        <HeaderActionButton
          id="slack-sync-btn"
          icon={RefreshCw}
          label="Sync"
          loading={syncing}
          onClick={onSync}
        >
          {syncing ? "Syncing..." : "Sync"}
        </HeaderActionButton>
        <HeaderActionButton
          id="slack-refresh-btn"
          icon={RefreshCw}
          label="Refresh"
          loading={loadingMessages}
          onClick={onRefresh}
        />
        <HeaderActionButton
          id="slack-agent-toggle"
          icon={Sparkles}
          label="Agent"
          active={agentOpen}
          onClick={onToggleAgent}
        />
      </div>
    </header>
  )
}
