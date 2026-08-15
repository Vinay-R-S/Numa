"use client"

/**
 * LeetCode panel data hook (NUMA-117 P4, PLAN 17.5 / 21.2).
 *
 * Owns the four state fields and the two effects the page's `LeetCodeSection`
 * held: resolving the tracked username (localStorage first, then the configured
 * integration key) and loading that user's public stats.
 *
 * Fetch timing is unchanged: the username resolves once on mount, a stored one
 * short-circuits the integration-keys read, and the stats read re-runs whenever
 * the username changes. The integration-keys failure stays swallowed - it is a
 * best-effort prefill, and surfacing it would replace the "add your username in
 * Settings" hint with an error the user cannot act on.
 */
import { useCallback, useEffect, useState } from "react"

import { getIntegrationKeys, getLeetCodeStats } from "./productivity.api"
import type { LeetCodeStats } from "./productivity.types"
import {
  errorMessage,
  readStoredLeetCodeUsername,
  storeLeetCodeUsername,
} from "./productivity.utils"

export function useLeetCode() {
  const [username, setUsername] = useState("")
  const [stats, setStats] = useState<LeetCodeStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const saved = readStoredLeetCodeUsername()
    if (saved) {
      setUsername(saved)
      return
    }

    getIntegrationKeys()
      .then((keys) => {
        const configured = keys.leetcode_username_value
        if (!configured) return
        setUsername(configured)
        storeLeetCodeUsername(configured)
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  const loadStats = useCallback(async (user: string) => {
    if (!user) return
    setLoading(true)
    setError(null)
    try {
      setStats(await getLeetCodeStats(user))
    } catch (err) {
      setError(errorMessage(err, "Failed to load LeetCode data"))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    if (username) void loadStats(username)
  }, [username, loadStats])

  return { username, stats, loading, error }
}

export type UseLeetCodeReturn = ReturnType<typeof useLeetCode>
