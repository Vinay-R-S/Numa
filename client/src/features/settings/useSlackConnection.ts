"use client"

/**
 * Slack connection panel hook (NUMA-119 P5, PLAN 17.1 / 21.2).
 *
 * Owns the four Slack status fields the settings page held inline. `connectSlack`
 * navigates the browser to the Slack consent screen itself, so `connecting`
 * stays set on success for the same reason as the calendar hook.
 */
import { useCallback, useEffect, useState } from "react"

import { connectSlack, getSlackStatus } from "@/features/slack/slack.api"
import type { SlackStatus } from "@/features/slack/slack.types"
import { errorMessage, slackStatusLabel } from "./settings.utils"

export function useSlackConnection() {
  const [status, setStatus] = useState<SlackStatus | null>(null)
  const [checking, setChecking] = useState(false)
  const [connecting, setConnecting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const check = useCallback(async () => {
    setChecking(true)
    setError(null)
    try {
      setStatus(await getSlackStatus())
    } catch (err) {
      setError(errorMessage(err, "Slack status check failed"))
    } finally {
      setChecking(false)
    }
  }, [])

  useEffect(() => {
    void check()
  }, [check])

  const reconnect = useCallback(async () => {
    setConnecting(true)
    setError(null)
    try {
      await connectSlack()
    } catch (err) {
      setError(errorMessage(err, "Could not start Slack OAuth"))
      setConnecting(false)
    }
  }, [])

  return {
    status,
    checking,
    connecting,
    error,
    statusLabel: slackStatusLabel(checking, status),
    needsReconnect: !checking && !status?.connected,
    check,
    reconnect,
  }
}

export type UseSlackConnectionReturn = ReturnType<typeof useSlackConnection>
