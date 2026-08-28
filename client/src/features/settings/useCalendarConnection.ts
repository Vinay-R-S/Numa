"use client"

/**
 * Google Calendar connection panel hook (NUMA-119 P5, PLAN 17.1 / 21.2).
 *
 * Owns the four token-health state fields and the reconnect action the settings
 * page held inline. The reconnect precedence is unchanged: a `reconnect_url`
 * from the health probe wins, otherwise a fresh authorization URL is requested.
 * `connecting` is deliberately left set on a successful start - the browser is
 * navigating away, so clearing it would only flash the button back.
 */
import { useCallback, useEffect, useState } from "react"

import {
  checkCalendarTokenHealth,
  getGoogleCalendarAuthorizationUrl,
} from "@/features/calendar/calendar.api"
import type { TokenHealthResult } from "@/features/calendar/calendar.types"
import { calendarStatusLabel, errorMessage } from "./settings.utils"

export function useCalendarConnection() {
  const [health, setHealth] = useState<TokenHealthResult | null>(null)
  const [checking, setChecking] = useState(false)
  const [connecting, setConnecting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const check = useCallback(async () => {
    setChecking(true)
    setError(null)
    try {
      setHealth(await checkCalendarTokenHealth())
    } catch (err) {
      setError(errorMessage(err, "Health check failed"))
    } finally {
      setChecking(false)
    }
  }, [])

  useEffect(() => {
    void check()
  }, [check])

  const reconnect = useCallback(async () => {
    if (health?.reconnect_url) {
      globalThis.location.href = health.reconnect_url
      return
    }

    setConnecting(true)
    setError(null)
    try {
      globalThis.location.href = await getGoogleCalendarAuthorizationUrl()
    } catch (err) {
      setError(errorMessage(err, "Could not start Google OAuth"))
      setConnecting(false)
    }
  }, [health])

  return {
    health,
    checking,
    connecting,
    error,
    status: calendarStatusLabel(checking, health),
    needsReconnect: !checking && health !== null && !health.valid,
    check,
    reconnect,
  }
}

export type UseCalendarConnectionReturn = ReturnType<typeof useCalendarConnection>
