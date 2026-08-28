"use client"

/**
 * Integration keys panel hook (NUMA-119 P5, PLAN 17.1 / 21.2).
 *
 * Owns the seven state fields `IntegrationKeysSection` held inside
 * `settings/page.tsx`, now reading and writing through `settings.api` instead
 * of two hand-rolled `fetch` calls.
 *
 * Behavior carried over: only non-empty trimmed values are sent, saving with
 * nothing filled in is refused with the same message, saved fields are cleared
 * from the form while the status dots flip to configured, and a saved LeetCode
 * username is mirrored into the storage key the productivity page reads.
 */
import { useCallback, useEffect, useState } from "react"

import { storeLeetCodeUsername } from "@/features/productivity/productivity.utils"
import { getIntegrationKeysStatus, updateIntegrationKeys } from "./settings.api"
import {
  KEYS_SAVE_ERROR_TIMEOUT_MS,
  KEYS_SUCCESS_TIMEOUT_MS,
  KEYS_VALIDATION_TIMEOUT_MS,
} from "./settings.constants"
import type { IntegrationGroup, IntegrationKeysStatus } from "./settings.types"
import { errorMessage, prefillsFromStatus } from "./settings.utils"

export function useIntegrationKeys() {
  const [keysStatus, setKeysStatus] = useState<IntegrationKeysStatus>({})
  const [values, setValues] = useState<Record<string, string>>({})
  const [visibility, setVisibility] = useState<Record<string, boolean>>({})
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  useEffect(() => {
    getIntegrationKeysStatus()
      .then((status) => {
        setKeysStatus(status)
        setValues((prev) => ({ ...prev, ...prefillsFromStatus(status) }))
      })
      .catch((err) => setError(errorMessage(err, "Failed to load key status")))
      .finally(() => setLoading(false))
  }, [])

  const setValue = useCallback((key: string, value: string) => {
    setValues((prev) => ({ ...prev, [key]: value }))
  }, [])

  const toggleVisibility = useCallback((key: string) => {
    setVisibility((prev) => ({ ...prev, [key]: !prev[key] }))
  }, [])

  const isConfigured = useCallback(
    (key: string) => keysStatus[key] === true,
    [keysStatus]
  )

  const isVisible = useCallback((key: string) => visibility[key] ?? false, [visibility])

  const rejectEmpty = useCallback((message: string) => {
    setError(message)
    setTimeout(() => setError(null), KEYS_VALIDATION_TIMEOUT_MS)
  }, [])

  const saveKeys = useCallback(async (payload: Record<string, string>) => {
    setSaving(true)
    setError(null)
    setSuccess(null)
    try {
      const result = await updateIntegrationKeys(payload)
      const updated = result.updated || []

      setKeysStatus((prev) => {
        const next = { ...prev }
        updated.forEach((key) => { next[key] = true })
        return next
      })

      if (payload.leetcode_username) storeLeetCodeUsername(payload.leetcode_username)

      // Clear only the saved fields, so an unsaved group keeps what was typed.
      setValues((prev) => {
        const next = { ...prev }
        updated.forEach((key) => { delete next[key] })
        return next
      })

      setSuccess(`Saved ${updated.length} key(s) successfully!`)
      setTimeout(() => setSuccess(null), KEYS_SUCCESS_TIMEOUT_MS)
    } catch (err) {
      setError(errorMessage(err, "Failed to save keys"))
      setTimeout(() => setError(null), KEYS_SAVE_ERROR_TIMEOUT_MS)
    } finally {
      setSaving(false)
    }
  }, [])

  const saveGroup = useCallback(
    (group: IntegrationGroup) => {
      const payload: Record<string, string> = {}
      group.fields.forEach((field) => {
        const value = (values[field.key] ?? "").trim()
        if (value) payload[field.key] = value
      })

      if (Object.keys(payload).length === 0) {
        rejectEmpty(`Enter at least one ${group.label} value to save.`)
        return
      }

      void saveKeys(payload)
    },
    [rejectEmpty, saveKeys, values]
  )

  const saveAll = useCallback(() => {
    const payload: Record<string, string> = {}
    Object.entries(values).forEach(([key, value]) => {
      if (value.trim()) payload[key] = value.trim()
    })

    if (Object.keys(payload).length === 0) {
      rejectEmpty("Enter at least one value to save.")
      return
    }

    void saveKeys(payload)
  }, [rejectEmpty, saveKeys, values])

  return {
    values,
    loading,
    saving,
    error,
    success,
    isConfigured,
    isVisible,
    setValue,
    toggleVisibility,
    saveGroup,
    saveAll,
  }
}

export type UseIntegrationKeysReturn = ReturnType<typeof useIntegrationKeys>
