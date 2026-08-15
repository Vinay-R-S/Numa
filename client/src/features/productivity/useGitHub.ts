"use client"

/**
 * GitHub panel data hook (NUMA-117 P4, PLAN 17.5 / 21.2).
 *
 * Owns the seven state fields and the single effect the page's `GitHubSection`
 * held: the connection status, the stats read (cached unless refreshed), the
 * OAuth handoff, the personal-access-token connect and the disconnect.
 *
 * Fetch timing is unchanged: status and stats load once on mount through the
 * same `load` callback the refresh button reuses, and a forced refresh drives
 * `refreshing` instead of `loading` so the panel keeps rendering its data.
 */
import { useCallback, useEffect, useState } from "react"

import {
  connectGitHub,
  connectGitHubToken,
  disconnectGitHub,
  getGitHubStats,
  getGitHubStatus,
} from "./productivity.api"
import { githubTokenConnectSchema } from "./productivity.schema"
import type { GitHubAuthStatus, GitHubStats } from "./productivity.types"
import { errorMessage } from "./productivity.utils"

export function useGitHub() {
  const [status, setStatus] = useState<GitHubAuthStatus | null>(null)
  const [stats, setStats] = useState<GitHubStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [connectingToken, setConnectingToken] = useState(false)
  const [token, setToken] = useState("")
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async (force = false) => {
    if (force) {
      setRefreshing(true)
    } else {
      setLoading(true)
    }
    setError(null)

    try {
      const nextStatus = await getGitHubStatus()
      setStatus(nextStatus)
      if (nextStatus.connected) setStats(await getGitHubStats(force))
    } catch (err) {
      setError(errorMessage(err, "Failed to load GitHub data"))
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  const startOAuth = useCallback(async () => {
    try {
      globalThis.location.href = await connectGitHub()
    } catch (err) {
      setError(errorMessage(err, "Failed to connect"))
    }
  }, [])

  const connectWithToken = useCallback(async () => {
    // Mirrors GitHubTokenConnectRequest so an empty paste never reaches the API.
    const parsed = githubTokenConnectSchema.safeParse({ access_token: token })
    if (!parsed.success) {
      setError(parsed.error.issues[0]?.message || "Paste a GitHub token first")
      return
    }

    setConnectingToken(true)
    setError(null)
    try {
      setStatus(await connectGitHubToken(parsed.data.access_token))
      setToken("")
      setStats(await getGitHubStats(true))
    } catch (err) {
      setError(errorMessage(err, "Failed to connect GitHub token"))
    } finally {
      setConnectingToken(false)
    }
  }, [token])

  const disconnect = useCallback(async () => {
    try {
      await disconnectGitHub()
      setStatus({ connected: false })
      setStats(null)
    } catch (err) {
      setError(errorMessage(err, "Failed to disconnect"))
    }
  }, [])

  return {
    status,
    stats,
    loading,
    refreshing,
    connectingToken,
    token,
    error,
    connected: Boolean(status?.connected),
    setToken,
    load,
    startOAuth,
    connectWithToken,
    disconnect,
  }
}

export type UseGitHubReturn = ReturnType<typeof useGitHub>
