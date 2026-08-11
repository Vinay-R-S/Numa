"use client"

import { RefreshCw, Slack, Wifi, WifiOff } from "lucide-react"

import { Button } from "@/components/ui/button"
import type { SlackStatus } from "../slack.types"

interface ConnectionBannerProps {
  status: SlackStatus | null
  onConnect: () => void | Promise<void>
}

export function ConnectionBanner({ status, onConnect }: ConnectionBannerProps) {
  if (!status) {
    return (
      <div className="flex items-center gap-3 rounded-xl border border-border/30 bg-card/60 px-5 py-3 text-sm text-muted-foreground">
        <RefreshCw className="h-4 w-4 animate-spin text-primary/60" />
        Checking Slack connection…
      </div>
    )
  }

  if (status.connected) {
    return (
      <div className="flex items-center gap-3 rounded-xl border border-emerald-500/20 bg-emerald-500/5 px-5 py-3">
        <Wifi className="h-4 w-4 text-emerald-400" />
        <span className="text-sm font-medium text-emerald-400">
          Connected to {status.team_name || "Slack"}
        </span>
        {status.bot_configured && (
          <span className="ml-auto rounded-full border border-emerald-500/20 bg-emerald-500/10 px-2.5 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-emerald-400">
            Bot Active
          </span>
        )}
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-3 rounded-xl border border-[#E01E5A]/20 bg-[#E01E5A]/5 px-5 py-4 sm:flex-row sm:items-center">
      <div className="flex items-center gap-3 flex-1 min-w-0">
        <WifiOff className="h-4 w-4 shrink-0 text-[#E01E5A]" />
        <div>
          <p className="text-sm font-medium text-foreground">Slack not connected</p>
          <p className="text-xs text-muted-foreground">Connect your Slack workspace to use the Slack agent</p>
        </div>
      </div>
      <Button
        id="slack-connect-btn"
        size="sm"
        onClick={() => { void onConnect() }}
        className="shrink-0 bg-[#E01E5A] text-white hover:bg-[#c91a4d] border-none"
      >
        <Slack className="mr-2 h-3.5 w-3.5" />
        Connect Slack
      </Button>
    </div>
  )
}
