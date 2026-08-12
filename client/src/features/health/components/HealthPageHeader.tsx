"use client"

import { Activity, RefreshCw, Sparkles } from "lucide-react"

import { HeaderActionButton } from "@/components/ui/header-action-button"
import { LiveDataPill } from "@/components/ui/live-data-pill"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { formatDateLabel } from "../health.utils"

interface HealthPageHeaderProps {
  selectedDate: string
  availableDates: string[]
  live: boolean
  loading: boolean
  configured: boolean
  syncing: boolean
  agentOpen: boolean
  onSelectDate: (date: string) => void
  onSync: () => void
  onRefresh: () => void
  onToggleAgent: () => void
}

export function HealthPageHeader({
  selectedDate,
  availableDates,
  live,
  loading,
  configured,
  syncing,
  agentOpen,
  onSelectDate,
  onSync,
  onRefresh,
  onToggleAgent,
}: HealthPageHeaderProps) {
  return (
    <header className="flex flex-col gap-3 rounded-2xl border border-border/40 bg-card/40 p-4 sm:flex-row sm:items-center sm:justify-between sm:p-5">
      <div className="flex items-center gap-3">
        <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-muted/30 ring-1 ring-border/50">
          <Activity className="h-5 w-5 text-foreground" />
        </div>
        <div>
          <h1 className="text-xl font-bold tracking-tight text-foreground sm:text-2xl">
            Health Dashboard
          </h1>
          <p className="text-xs text-muted-foreground sm:text-sm">
            Google Fit + Strava &bull; 7-day rolling window &bull; Synced to Supabase
          </p>
        </div>
      </div>

      <div className="flex items-center gap-2">
        <Select value={selectedDate} onValueChange={onSelectDate}>
          <SelectTrigger className="h-9 w-[142px] border-border/40 bg-background/40 text-xs">
            <SelectValue placeholder="Select day" />
          </SelectTrigger>
          <SelectContent>
            {availableDates.map((dateKey) => (
              <SelectItem key={dateKey} value={dateKey}>
                {formatDateLabel(dateKey)}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <LiveDataPill live={live} loading={loading} configured={configured} />
        <HeaderActionButton icon={RefreshCw} label="Sync" loading={syncing} onClick={onSync}>
          {syncing ? "Syncing..." : "Sync"}
        </HeaderActionButton>
        <HeaderActionButton icon={RefreshCw} label="Refresh" loading={loading} onClick={onRefresh} />
        <HeaderActionButton
          icon={Sparkles}
          label="Agent"
          active={agentOpen}
          onClick={onToggleAgent}
        />
      </div>
    </header>
  )
}
