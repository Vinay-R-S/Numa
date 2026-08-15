"use client"

import { Loader2 } from "lucide-react"

import { Button } from "@/components/ui/button"

import { useGitHub } from "../useGitHub"
import { GitHubConnectPanel } from "./GitHubConnectPanel"
import { GitHubProfileHeader } from "./GitHubProfileHeader"
import { GitHubStatsGrid } from "./GitHubStatsGrid"
import { RecentCommitsList } from "./RecentCommitsList"
import { RecentReposList } from "./RecentReposList"
import { SectionErrorBanner } from "./SectionErrorBanner"

export function GitHubSection() {
  const {
    stats,
    loading,
    refreshing,
    connectingToken,
    token,
    error,
    connected,
    setToken,
    load,
    startOAuth,
    connectWithToken,
    disconnect,
  } = useGitHub()

  if (loading) {
    return (
      <div className="flex items-center justify-center py-16">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="space-y-3">
        <SectionErrorBanner message={error} />
        <Button variant="ghost" size="sm" onClick={() => void load()}>
          Retry
        </Button>
      </div>
    )
  }

  if (!connected) {
    return (
      <GitHubConnectPanel
        token={token}
        connecting={connectingToken}
        onTokenChange={setToken}
        onConnectOAuth={() => { void startOAuth() }}
        onConnectToken={() => { void connectWithToken() }}
      />
    )
  }

  return (
    <div className="space-y-5">
      <GitHubProfileHeader
        stats={stats}
        connected={connected}
        refreshing={refreshing}
        onRefresh={() => { void load(true) }}
        onDisconnect={() => { void disconnect() }}
      />

      <GitHubStatsGrid stats={stats} />

      <RecentReposList repos={stats?.recent_repos ?? []} />

      <RecentCommitsList commits={stats?.recent_commits ?? []} />
    </div>
  )
}
