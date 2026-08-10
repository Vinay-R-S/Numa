"use client"

import { CalendarDays, RefreshCw, Search, Sparkles } from "lucide-react"

import { HeaderActionButton } from "@/components/ui/header-action-button"
import { LiveDataPill } from "@/components/ui/live-data-pill"

interface CalendarPageHeaderProps {
  live: boolean
  loading: boolean
  configured: boolean
  searchQuery: string
  refreshing: boolean
  agentOpen: boolean
  onSearchChange: (value: string) => void
  onRefresh: () => void
  onToggleAgent: () => void
}

export function CalendarPageHeader({
  live,
  loading,
  configured,
  searchQuery,
  refreshing,
  agentOpen,
  onSearchChange,
  onRefresh,
  onToggleAgent,
}: CalendarPageHeaderProps) {
  const busy = refreshing || loading

  return (
    <header className="flex shrink-0 flex-col gap-3 rounded-2xl border border-border/40 bg-card/40 p-4 sm:flex-row sm:items-center sm:justify-between sm:p-5">
      <div className="flex items-center gap-3">
        <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-muted/30 ring-1 ring-border/50">
          <CalendarDays className="h-5 w-5 text-foreground" />
        </div>
        <div className="min-w-0">
          <h1 className="truncate text-xl font-bold tracking-tight text-foreground sm:text-2xl">Calendar</h1>
          <p className="hidden text-sm text-muted-foreground sm:block">
            Manage Google Calendar events directly from NUMA
          </p>
        </div>
      </div>

      <div className="flex w-full flex-wrap items-center gap-2 sm:w-auto sm:max-w-3xl sm:justify-end">
        <LiveDataPill live={live} loading={loading} configured={configured} />
        <div className="relative flex-1 sm:w-full sm:max-w-md">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground/60" />
          <input
            type="text"
            value={searchQuery}
            onChange={(event) => onSearchChange(event.target.value)}
            placeholder="Search events"
            className="h-9 w-full rounded-xl border border-border/40 bg-card px-9 py-2 text-sm text-foreground placeholder:text-muted-foreground/50 focus:outline-none focus:ring-1 focus:ring-primary/30 sm:h-10"
          />
        </div>

        <HeaderActionButton
          icon={RefreshCw}
          label="Refresh"
          loading={busy}
          onClick={onRefresh}
          disabled={busy}
          title={busy ? "Refreshing calendar" : "Refresh calendar"}
        />

        <HeaderActionButton icon={Sparkles} label="Agent" active={agentOpen} onClick={onToggleAgent} />
      </div>
    </header>
  )
}
