import Image from "next/image"
import { GitBranch, RefreshCw, Unlink } from "lucide-react"

import { HeaderActionButton } from "@/components/ui/header-action-button"
import { LiveDataPill } from "@/components/ui/live-data-pill"

import type { GitHubStats } from "../productivity.types"

export function GitHubProfileHeader({
  stats,
  connected,
  refreshing,
  onRefresh,
  onDisconnect,
}: {
  stats: GitHubStats | null
  connected: boolean
  refreshing: boolean
  onRefresh: () => void
  onDisconnect: () => void
}) {
  return (
    <div className="flex items-center justify-between">
      <div className="flex items-center gap-3">
        {stats?.avatar_url ? (
          <Image
            src={stats.avatar_url}
            alt={stats.username}
            width={40}
            height={40}
            unoptimized
            className="h-10 w-10 rounded-full ring-2 ring-border/40"
          />
        ) : (
          <div className="flex h-10 w-10 items-center justify-center rounded-full bg-primary/10 ring-2 ring-border/40">
            <GitBranch className="h-5 w-5 text-primary" />
          </div>
        )}
        <div>
          <p className="text-sm font-bold text-foreground">{stats?.username}</p>
          <p className="text-[11px] text-muted-foreground">
            {stats?.followers} followers &middot; {stats?.following} following
          </p>
        </div>
      </div>
      <div className="flex items-center gap-2">
        <LiveDataPill live={Boolean(stats)} loading={refreshing} configured={connected} />
        <HeaderActionButton
          icon={RefreshCw}
          label="Refresh"
          loading={refreshing}
          onClick={onRefresh}
          disabled={refreshing}
        >
          {refreshing ? "Refreshing" : "Refresh"}
        </HeaderActionButton>
        <HeaderActionButton
          icon={Unlink}
          label="Disconnect"
          onClick={onDisconnect}
          className="hover:border-destructive/50 hover:text-destructive"
        />
      </div>
    </div>
  )
}
