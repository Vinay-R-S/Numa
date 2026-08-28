"use client"

/**
 * AI provider panel data hook (NUMA-119 P5, PLAN 17.1 / 21.2).
 *
 * Owns the 15 state fields the settings page held for the provider section plus
 * the local agent kill switch, and the two effects behind them: the initial
 * `/ai-settings` load and the Ollama tag lookup that re-runs whenever the
 * provider or the base URL changes.
 *
 * Fetch timing is unchanged: settings load once on mount, the Ollama list is
 * only requested while `ollama` is the selected provider, and a failed lookup
 * empties the list instead of surfacing an error (the panel already explains
 * that Ollama has to be running). One fix on the way over: the lookup re-fires
 * on every keystroke in the base URL field, so a superseded response used to be
 * able to land last and overwrite the current model list; stale responses are
 * now ignored.
 */
import { useCallback, useEffect, useMemo, useState } from "react"

import { getAiSettings, getOllamaModels, resetAiSettings, updateAiSettings } from "./settings.api"
import {
  AI_MESSAGE_TIMEOUT_MS,
  DEFAULT_OLLAMA_URL,
  DEFAULT_PROVIDER,
  DEFAULT_TEMPERATURE,
} from "./settings.constants"
import type { AiProvider, AiSettings, ProviderInfo } from "./settings.types"
import { getLocalAiEnabled, setLocalAiEnabled } from "./settings.storage"
import { errorMessage } from "./settings.utils"

export function useAiSettings() {
  const [aiEnabled, setAiEnabled] = useState(() => getLocalAiEnabled())

  const [providers, setProviders] = useState<ProviderInfo[]>([])
  const [currentSettings, setCurrentSettings] = useState<AiSettings | null>(null)
  const [selectedProvider, setSelectedProvider] = useState<AiProvider>(DEFAULT_PROVIDER)
  const [selectedModel, setSelectedModel] = useState("")
  const [apiKey, setApiKey] = useState("")
  const [showApiKey, setShowApiKey] = useState(false)
  const [ollamaUrl, setOllamaUrl] = useState(DEFAULT_OLLAMA_URL)
  const [temperature, setTemperature] = useState(DEFAULT_TEMPERATURE)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)
  const [modelOpen, setModelOpen] = useState(false)
  const [ollamaModels, setOllamaModels] = useState<string[]>([])
  const [ollamaLoading, setOllamaLoading] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await getAiSettings()
      setProviders(data.providers)

      if (data.current) {
        setCurrentSettings(data.current)
        setSelectedProvider(data.current.provider)
        setSelectedModel(data.current.model_id)
        setOllamaUrl(data.current.ollama_base_url || DEFAULT_OLLAMA_URL)
        setTemperature(data.current.temperature)
        return
      }

      if (data.providers.length === 0) return
      // Prefer a provider that already has a server-side key over the first one.
      const first = data.providers.find((p) => p.configured_via_env) || data.providers[0]
      setSelectedProvider(first.id)
      setSelectedModel(first.default_model)
    } catch (err) {
      setError(errorMessage(err, "Failed to load AI settings"))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  useEffect(() => {
    if (selectedProvider !== "ollama") return undefined

    let current = true
    setOllamaLoading(true)
    getOllamaModels(ollamaUrl)
      .then((models) => { if (current) setOllamaModels(models) })
      .catch(() => { if (current) setOllamaModels([]) })
      .finally(() => { if (current) setOllamaLoading(false) })

    return () => { current = false }
  }, [selectedProvider, ollamaUrl])

  const toggleAi = useCallback(() => {
    const next = !aiEnabled
    setAiEnabled(next)
    setLocalAiEnabled(next)
  }, [aiEnabled])

  const selectProvider = useCallback(
    (providerId: AiProvider) => {
      setSelectedProvider(providerId)
      const provider = providers.find((p) => p.id === providerId)
      if (provider) setSelectedModel(provider.default_model)
      setApiKey("")
      setShowApiKey(false)
      setError(null)
      setSuccess(null)
    },
    [providers]
  )

  const selectModel = useCallback((model: string) => {
    setSelectedModel(model)
    setModelOpen(false)
  }, [])

  const save = useCallback(async () => {
    setSaving(true)
    setError(null)
    setSuccess(null)
    try {
      const result = await updateAiSettings({
        provider: selectedProvider,
        model_id: selectedModel,
        api_key: apiKey || undefined,
        ollama_base_url: selectedProvider === "ollama" ? ollamaUrl : undefined,
        temperature,
      })
      setCurrentSettings(result)
      setApiKey("")
      setShowApiKey(false)
      setSuccess("AI settings saved successfully!")
      setTimeout(() => setSuccess(null), AI_MESSAGE_TIMEOUT_MS)
    } catch (err) {
      setError(errorMessage(err, "Failed to save settings"))
    } finally {
      setSaving(false)
    }
  }, [apiKey, ollamaUrl, selectedModel, selectedProvider, temperature])

  const reset = useCallback(async () => {
    setSaving(true)
    setError(null)
    try {
      await resetAiSettings()
      setCurrentSettings(null)
      setApiKey("")
      await load()
      setSuccess("Settings reset to server defaults")
      setTimeout(() => setSuccess(null), AI_MESSAGE_TIMEOUT_MS)
    } catch (err) {
      setError(errorMessage(err, "Failed to reset settings"))
    } finally {
      setSaving(false)
    }
  }, [load])

  const selectedProviderInfo = useMemo(
    () => providers.find((p) => p.id === selectedProvider),
    [providers, selectedProvider]
  )

  // Ollama reports what is actually pulled locally; every other provider has a
  // fixed catalogue.
  const modelOptions = useMemo(() => {
    if (selectedProvider === "ollama" && ollamaModels.length > 0) return ollamaModels
    return selectedProviderInfo?.models ?? []
  }, [ollamaModels, selectedProvider, selectedProviderInfo])

  return {
    aiEnabled,
    providers,
    currentSettings,
    selectedProvider,
    selectedProviderInfo,
    selectedModel,
    modelOptions,
    modelOpen,
    apiKey,
    showApiKey,
    ollamaUrl,
    ollamaModels,
    ollamaLoading,
    temperature,
    loading,
    saving,
    error,
    success,
    setModelOpen,
    setApiKey,
    setShowApiKey,
    setOllamaUrl,
    setTemperature,
    selectProvider,
    selectModel,
    toggleAi,
    save,
    reset,
  }
}

export type UseAiSettingsReturn = ReturnType<typeof useAiSettings>
