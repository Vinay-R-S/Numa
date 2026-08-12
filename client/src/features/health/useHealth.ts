"use client"

/**
 * Health dashboard data hook (NUMA-116 P4, PLAN 17.2 / 21.2).
 *
 * Owns everything the page used to hold in 8 state fields and 4 effects: the
 * status roll-up, the 8-day snapshot window, the selected day's hourly buckets,
 * the sync/refresh actions and the derived day list.
 *
 * Fetch timing is unchanged: snapshots load once on mount, the intraday read
 * re-runs whenever the selected date or the snapshot list changes and drops its
 * result if a newer read started (the same `cancelled` guard the page used, so
 * an in-flight request is still left to finish rather than aborted), and the
 * selected date resets only when it falls outside the available days.
 */
import { useCallback, useEffect, useMemo, useState } from "react"

import { getHealthIntraday, getHealthSnapshots, getHealthStatus, syncAllHealth } from "./health.api"
import { SNAPSHOT_DAYS } from "./health.constants"
import type {
  HealthIntraday,
  HealthSnapshot,
  HealthStatus,
  HealthSyncAllResult,
} from "./health.types"
import { localDateString } from "./health.utils"

const SYNC_EMPTY_MESSAGE = "No recent health data was returned from Google Fit or Strava"

export function useHealth() {
  const [status, setStatus] = useState<HealthStatus | null>(null)
  const [snapshots, setSnapshots] = useState<HealthSnapshot[]>([])
  const [intraday, setIntraday] = useState<HealthIntraday | null>(null)
  const [intradayLoading, setIntradayLoading] = useState(false)
  const [intradayError, setIntradayError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [syncing, setSyncing] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [selectedDate, setSelectedDate] = useState(localDateString())

  const loadData = useCallback(async () => {
    setLoading(true)
    try {
      const [nextStatus, nextSnapshots] = await Promise.all([
        getHealthStatus(),
        getHealthSnapshots({ days: SNAPSHOT_DAYS }),
      ])
      setStatus(nextStatus)
      setSnapshots(nextSnapshots)
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load health data")
    } finally {
      setLoading(false)
    }
  }, [])

  const syncHealth = useCallback(async () => {
    setSyncing(true)
    let result: HealthSyncAllResult | null = null
    let failure: string | null = null

    try {
      result = await syncAllHealth()
    } catch (err) {
      failure = err instanceof Error ? err.message : "Failed to sync health data"
    }

    try {
      // Always refetch: the providers may have been synced server-side even when
      // reading the response failed, and the old code's early return would have
      // hidden those fresh snapshots until a manual reload.
      await loadData()
      if (failure) {
        setError(failure)
        return
      }
      if (result && !result.ok) {
        setError(result.detail || SYNC_EMPTY_MESSAGE)
        return
      }
      if (result?.detail) setError(null)
    } finally {
      setSyncing(false)
    }
  }, [loadData])

  useEffect(() => {
    void loadData()
  }, [loadData])

  useEffect(() => {
    let cancelled = false
    setIntradayLoading(true)

    getHealthIntraday({ snapshotDate: selectedDate })
      .then((data) => {
        if (cancelled) return
        setIntraday(data)
        setIntradayError(null)
      })
      .catch((err) => {
        if (cancelled) return
        setIntraday(null)
        // A failed read is not the same as "nothing synced yet": without this the
        // chart tells a connected user to run Sync, forever.
        setIntradayError(err instanceof Error ? err.message : "Failed to fetch daily health data")
      })
      .finally(() => {
        if (!cancelled) setIntradayLoading(false)
      })

    return () => {
      cancelled = true
    }
  }, [selectedDate, snapshots])

  const todayStr = localDateString()

  const availableDates = useMemo(() => {
    const dates = Array.from(new Set(snapshots.map((snapshot) => snapshot.snapshot_date))).sort(
      (a, b) => b.localeCompare(a)
    )

    return dates.length > 0 ? dates : [todayStr]
  }, [snapshots, todayStr])

  useEffect(() => {
    if (!availableDates.includes(selectedDate)) {
      setSelectedDate(availableDates[0] ?? todayStr)
    }
  }, [availableDates, selectedDate, todayStr])

  const selectedSnapshot = useMemo(
    () =>
      snapshots.find(
        (snapshot) => snapshot.source === "google_fit" && snapshot.snapshot_date === selectedDate
      ) || null,
    [snapshots, selectedDate]
  )

  return {
    status,
    snapshots,
    intraday,
    intradayLoading,
    intradayError,
    loading,
    syncing,
    error,
    selectedDate,
    availableDates,
    selectedSnapshot,
    isLive: snapshots.length > 0,
    isConfigured: Boolean(status?.google_fit_configured || status?.strava_configured),
    setSelectedDate,
    loadData,
    syncHealth,
  }
}

export type UseHealthReturn = ReturnType<typeof useHealth>
