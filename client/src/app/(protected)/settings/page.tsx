"use client"

import React, { useCallback, useEffect, useState } from "react"
import {
  Bot, Calendar, CheckCircle2, XCircle, RefreshCw, AlertTriangle, Loader2,
  Key, Server, Thermometer, ChevronDown, RotateCcw, Eye, EyeOff, Save,
  Slack, Timer,
} from "lucide-react"

import { Button } from "@/components/ui/button"
import { HeaderActionButton } from "@/components/ui/header-action-button"
import { LiveDataPill } from "@/components/ui/live-data-pill"
import { cn } from "@/lib/utils"
import {
  type AiProvider,
  type AiSettings,
  type ProviderInfo,
  fetchAiSettings,
  updateAiSettings,
  resetAiSettings,
  getLocalAiEnabled,
  setLocalAiEnabled,
} from "@/lib/aiSettings"
import {
  checkCalendarTokenHealth,
  getGoogleCalendarAuthorizationUrl,
  TokenHealthResult,
} from "@/components/calendar/api"
import {
  connectSlack,
  getSlackStatus,
  type SlackStatus,
} from "@/components/agents/slackAgentApi"

function clampInteger(value: number, min: number, max: number, fallback: number): number {
  if (!Number.isFinite(value)) return fallback
  return Math.min(max, Math.max(min, Math.round(value)))
}

function parseBoundedInput(value: string | number, min: number, max: number, fallback: number): number {
  const parsed = typeof value === "number" ? value : Number.parseInt(value, 10)
  return clampInteger(parsed, min, max, fallback)
}

const PROVIDER_ICONS: Record<string, React.ReactNode> = {
  groq: <span className="text-[10px] font-black tracking-tight text-orange-400">GROQ</span>,
  openai: <span className="text-[10px] font-black tracking-tight text-green-400">GPT</span>,
  anthropic: <span className="text-[10px] font-black tracking-tight text-amber-400">CL</span>,
  gemini: <span className="text-[10px] font-black tracking-tight text-blue-400">GEM</span>,
  ollama: <span className="text-[10px] font-black tracking-tight text-violet-400">OLL</span>,
}

const PROVIDER_DESCRIPTIONS: Record<string, string> = {
  groq: "Ultra-fast inference with Llama, Mixtral, and Gemma models",
  openai: "GPT-4o, GPT-4 Turbo, and GPT-3.5 models",
  anthropic: "Claude Sonnet, Haiku, and Opus models",
  gemini: "Google Gemini 2.0 Flash and Gemini 1.5 models",
  ollama: "Run local models on your machine - no API key needed",
}

export default function SettingsPage() {
  const [aiEnabled, setAiEnabled] = useState(() => getLocalAiEnabled())

  // AI provider state
  const [providers, setProviders] = useState<ProviderInfo[]>([])
  const [currentSettings, setCurrentSettings] = useState<AiSettings | null>(null)
  const [selectedProvider, setSelectedProvider] = useState<AiProvider>("groq")
  const [selectedModel, setSelectedModel] = useState("")
  const [apiKey, setApiKey] = useState("")
  const [showApiKey, setShowApiKey] = useState(false)
  const [ollamaUrl, setOllamaUrl] = useState("http://localhost:11434")
  const [temperature, setTemperature] = useState(0.1)
  const [aiLoading, setAiLoading] = useState(true)
  const [aiSaving, setAiSaving] = useState(false)
  const [aiError, setAiError] = useState<string | null>(null)
  const [aiSuccess, setAiSuccess] = useState<string | null>(null)
  const [modelOpen, setModelOpen] = useState(false)
  const [ollamaModels, setOllamaModels] = useState<string[]>([])
  const [ollamaLoading, setOllamaLoading] = useState(false)

  // Google Calendar token state
  const [tokenHealth, setTokenHealth] = useState<TokenHealthResult | null>(null)
  const [tokenChecking, setTokenChecking] = useState(false)
  const [tokenConnecting, setTokenConnecting] = useState(false)
  const [tokenError, setTokenError] = useState<string | null>(null)

  // Slack token state
  const [slackStatus, setSlackStatus] = useState<SlackStatus | null>(null)
  const [slackChecking, setSlackChecking] = useState(false)
  const [slackConnecting, setSlackConnecting] = useState(false)
  const [slackError, setSlackError] = useState<string | null>(null)

  // Timeline settings state
  const [tlInterval, setTlInterval] = useState(300_000)
  const [tlWaterEnabled, setTlWaterEnabled] = useState(true)
  const [tlWaterStart, setTlWaterStart] = useState("8")
  const [tlWaterEnd, setTlWaterEnd] = useState("22")
  const [tlWaterStep, setTlWaterStep] = useState("60")
  const [tlBreakfast, setTlBreakfast] = useState("08:00")
  const [tlLunch, setTlLunch] = useState("13:00")
  const [tlDinner, setTlDinner] = useState("20:00")
  const [tlSaved, setTlSaved] = useState(false)

  useEffect(() => {
    try {
      const raw = localStorage.getItem("numa_timeline_settings")
      if (!raw) return
      const s = JSON.parse(raw)
      if (s.updateIntervalMs) setTlInterval(s.updateIntervalMs)
      if (s.waterEnabled !== undefined) setTlWaterEnabled(s.waterEnabled)
      if (s.waterConfig) {
        setTlWaterStart(String(s.waterConfig.startHour ?? 8))
        setTlWaterEnd(String(s.waterConfig.endHour ?? 22))
        setTlWaterStep(String(s.waterConfig.stepMinutes ?? 60))
      }
      if (s.mealTimes) {
        setTlBreakfast(s.mealTimes.breakfast ?? "08:00")
        setTlLunch(s.mealTimes.lunch ?? "13:00")
        setTlDinner(s.mealTimes.dinner ?? "20:00")
      }
    } catch { /* ignore corrupt data */ }
  }, [])

  const handleSaveTimeline = () => {
    const startHour = parseBoundedInput(tlWaterStart, 0, 24, 8)
    const endHour = parseBoundedInput(tlWaterEnd, 0, 24, 22)
    const stepMinutes = parseBoundedInput(tlWaterStep, 1, 60, 60)
    setTlWaterStart(String(startHour))
    setTlWaterEnd(String(endHour))
    setTlWaterStep(String(stepMinutes))

    const settings = {
      updateIntervalMs: tlInterval,
      waterEnabled: tlWaterEnabled,
      waterConfig: { startHour, endHour, stepMinutes },
      mealTimes: { breakfast: tlBreakfast, lunch: tlLunch, dinner: tlDinner },
    }
    localStorage.setItem("numa_timeline_settings", JSON.stringify(settings))
    setTlSaved(true)
    setTimeout(() => setTlSaved(false), 2500)
  }

  const checkToken = useCallback(async () => {
    setTokenChecking(true)
    setTokenError(null)
    try {
      const result = await checkCalendarTokenHealth()
      setTokenHealth(result)
    } catch (err) {
      setTokenError(err instanceof Error ? err.message : "Health check failed")
    } finally {
      setTokenChecking(false)
    }
  }, [])

  const checkSlack = useCallback(async () => {
    setSlackChecking(true)
    setSlackError(null)
    try {
      const result = await getSlackStatus()
      setSlackStatus(result)
    } catch (err) {
      setSlackError(err instanceof Error ? err.message : "Slack status check failed")
    } finally {
      setSlackChecking(false)
    }
  }, [])

  const loadAiSettings = useCallback(async () => {
    setAiLoading(true)
    setAiError(null)
    try {
      const data = await fetchAiSettings()
      setProviders(data.providers)
      if (data.current) {
        setCurrentSettings(data.current)
        setSelectedProvider(data.current.provider as AiProvider)
        setSelectedModel(data.current.model_id)
        setOllamaUrl(data.current.ollama_base_url || "http://localhost:11434")
        setTemperature(data.current.temperature)
      } else if (data.providers.length > 0) {
        const envConfigured = data.providers.find((p) => p.configured_via_env)
        const first = envConfigured || data.providers[0]
        setSelectedProvider(first.id as AiProvider)
        setSelectedModel(first.default_model)
      }
    } catch (err) {
      setAiError(err instanceof Error ? err.message : "Failed to load AI settings")
    } finally {
      setAiLoading(false)
    }
  }, [])

  useEffect(() => {
    checkToken()
    checkSlack()
    loadAiSettings()
  }, [checkSlack, checkToken, loadAiSettings])

  useEffect(() => {
    if (selectedProvider !== "ollama") return
    setOllamaLoading(true)
    fetch(`${ollamaUrl}/api/tags`)
      .then((r) => r.json())
      .then((data) => {
        const models = (data?.models || []).map((m: { name: string }) => m.name)
        setOllamaModels(models)
      })
      .catch(() => setOllamaModels([]))
      .finally(() => setOllamaLoading(false))
  }, [selectedProvider, ollamaUrl])

  const handleReconnect = async () => {
    if (tokenHealth?.reconnect_url) {
      window.location.href = tokenHealth.reconnect_url
      return
    }
    setTokenConnecting(true)
    setTokenError(null)
    try {
      const url = await getGoogleCalendarAuthorizationUrl()
      window.location.href = url
    } catch (err) {
      setTokenError(err instanceof Error ? err.message : "Could not start Google OAuth")
      setTokenConnecting(false)
    }
  }

  const handleSlackReconnect = async () => {
    setSlackConnecting(true)
    setSlackError(null)
    try {
      await connectSlack()
    } catch (err) {
      setSlackError(err instanceof Error ? err.message : "Could not start Slack OAuth")
      setSlackConnecting(false)
    }
  }

  const handleToggleAi = () => {
    const next = !aiEnabled
    setAiEnabled(next)
    setLocalAiEnabled(next)
  }

  const handleProviderChange = (providerId: AiProvider) => {
    setSelectedProvider(providerId)
    const p = providers.find((x) => x.id === providerId)
    if (p) setSelectedModel(p.default_model)
    setApiKey("")
    setShowApiKey(false)
    setAiError(null)
    setAiSuccess(null)
  }

  const handleSaveAi = async () => {
    setAiSaving(true)
    setAiError(null)
    setAiSuccess(null)
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
      setAiSuccess("AI settings saved successfully!")
      setTimeout(() => setAiSuccess(null), 3000)
    } catch (err) {
      setAiError(err instanceof Error ? err.message : "Failed to save settings")
    } finally {
      setAiSaving(false)
    }
  }

  const handleResetAi = async () => {
    setAiSaving(true)
    setAiError(null)
    try {
      await resetAiSettings()
      setCurrentSettings(null)
      setApiKey("")
      await loadAiSettings()
      setAiSuccess("Settings reset to server defaults")
      setTimeout(() => setAiSuccess(null), 3000)
    } catch (err) {
      setAiError(err instanceof Error ? err.message : "Failed to reset settings")
    } finally {
      setAiSaving(false)
    }
  }

  const selectedProviderInfo = providers.find((p) => p.id === selectedProvider)

  const tokenStatusLabel = () => {
    if (tokenChecking) return { text: "Checking…", color: "text-muted-foreground", Icon: Loader2, spin: true }
    if (!tokenHealth) return { text: "Unknown", color: "text-muted-foreground", Icon: AlertTriangle, spin: false }
    if (tokenHealth.valid) return { text: "Connected & valid", color: "text-emerald-400", Icon: CheckCircle2, spin: false }
    if (tokenHealth.connected) return { text: "Token expired / revoked", color: "text-amber-400", Icon: AlertTriangle, spin: false }
    return { text: "Not connected", color: "text-rose-400", Icon: XCircle, spin: false }
  }

  const { text: statusText, color: statusColor, Icon: StatusIcon, spin: statusSpin } = tokenStatusLabel()
  const needsReconnect = !tokenChecking && tokenHealth !== null && !tokenHealth.valid

  const slackStatusLabel = () => {
    if (slackChecking) return { text: "Checking...", color: "text-muted-foreground", Icon: Loader2, spin: true }
    if (!slackStatus) return { text: "Unknown", color: "text-muted-foreground", Icon: AlertTriangle, spin: false }
    if (slackStatus.connected) return { text: "Connected", color: "text-emerald-400", Icon: CheckCircle2, spin: false }
    if (slackStatus.bot_configured) return { text: "Bot token configured", color: "text-amber-400", Icon: AlertTriangle, spin: false }
    return { text: "Not connected", color: "text-rose-400", Icon: XCircle, spin: false }
  }

  const {
    text: slackStatusText,
    color: slackStatusColor,
    Icon: SlackStatusIcon,
    spin: slackStatusSpin,
  } = slackStatusLabel()
  const needsSlackReconnect = !slackChecking && !slackStatus?.connected

  return (
    <div className="flex min-h-full w-full flex-col gap-4 px-4 py-4 sm:gap-6 sm:px-6 sm:py-6">
      <header className="flex flex-col gap-3 rounded-xl border border-border/40 bg-card/40 p-4 sm:flex-row sm:items-center sm:justify-between sm:rounded-2xl sm:p-5">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-foreground sm:text-2xl">Settings</h1>
          <p className="mt-1 text-xs text-muted-foreground sm:text-sm">
            Configure AI providers, model selection, and integrations.
          </p>
        </div>
        <LiveDataPill live={!aiLoading} loading={aiLoading} />
      </header>

      {/* ── AI Provider Configuration ──────────────────────────────────── */}
      <section className="rounded-xl border border-border/40 bg-card/40 p-4 sm:rounded-2xl sm:p-5">
        <div className="mb-4 flex items-start gap-3">
          <div className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-primary/10 ring-1 ring-primary/20 sm:h-9 sm:w-9">
            <Key className="h-4 w-4 text-primary" />
          </div>
          <div className="min-w-0">
            <h2 className="text-base font-semibold text-foreground sm:text-lg">AI Provider</h2>
            <p className="text-xs text-muted-foreground sm:text-sm">
              Choose your LLM provider and model. API keys are encrypted before storage.
            </p>
          </div>
        </div>

        {aiLoading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          </div>
        ) : (
          <div className="space-y-4">
            {/* Provider cards */}
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-5">
              {providers.map((p) => (
                <button
                  key={p.id}
                  type="button"
                  onClick={() => handleProviderChange(p.id as AiProvider)}
                  className={cn(
                    "relative rounded-xl border px-3 py-3 text-left transition-all",
                    selectedProvider === p.id
                      ? "border-primary/50 bg-primary/10 ring-1 ring-primary/30"
                      : "border-border/40 bg-background/40 hover:bg-accent/40"
                  )}
                >
                  <div className="mb-1 flex items-center gap-1.5">
                    <div className="flex h-5 w-5 items-center justify-center">{PROVIDER_ICONS[p.id] || <span className="text-[10px] font-bold text-muted-foreground">AI</span>}</div>
                    <span className="text-sm font-semibold text-foreground">{p.name}</span>
                  </div>
                  <p className="text-[10px] leading-tight text-muted-foreground line-clamp-2">
                    {PROVIDER_DESCRIPTIONS[p.id]}
                  </p>
                  {p.configured_via_env && (
                    <span className="absolute -top-1.5 -right-1.5 rounded-full bg-emerald-500/20 px-1.5 py-0.5 text-[9px] font-medium text-emerald-400 ring-1 ring-emerald-500/30">
                      ENV
                    </span>
                  )}
                </button>
              ))}
            </div>

            {/* Model selector */}
            <div className="rounded-xl border border-border/40 bg-background/40 p-3 sm:p-4">
              <div className="grid gap-3 sm:grid-cols-2">
                {/* Model dropdown */}
                <div>
                  <label className="mb-1.5 block text-xs font-medium text-muted-foreground">Model</label>
                  <div className="relative">
                    <button
                      type="button"
                      onClick={() => setModelOpen(!modelOpen)}
                      className="flex w-full items-center justify-between rounded-lg border border-border/60 bg-background/60 px-3 py-2 text-sm text-foreground transition-colors hover:bg-accent/40"
                    >
                      <span className="truncate">{selectedModel || "Select model"}</span>
                      <ChevronDown className={cn("h-3.5 w-3.5 shrink-0 text-muted-foreground transition-transform", modelOpen && "rotate-180")} />
                    </button>
                    {modelOpen && selectedProviderInfo && (
                      <div className="absolute z-20 mt-1 w-full rounded-lg border border-border/60 bg-card shadow-lg">
                        <div className="max-h-48 overflow-y-auto py-1">
                          {(selectedProvider === "ollama" && ollamaModels.length > 0 ? ollamaModels : selectedProviderInfo.models).map((m) => (
                            <button
                              key={m}
                              type="button"
                              className={cn(
                                "w-full px-3 py-1.5 text-left text-sm transition-colors hover:bg-accent/40",
                                m === selectedModel ? "bg-primary/10 font-medium text-primary" : "text-foreground"
                              )}
                              onClick={() => { setSelectedModel(m); setModelOpen(false) }}
                            >
                              {m}
                            </button>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                  {selectedProvider === "ollama" && ollamaModels.length === 0 && !ollamaLoading && (
                    <p className="mt-1 text-[10px] text-muted-foreground">No local models found. Make sure Ollama is running.</p>
                  )}
                  {selectedProvider === "ollama" && ollamaLoading && (
                    <p className="mt-1 text-[10px] text-muted-foreground flex items-center gap-1">
                      <Loader2 className="h-3 w-3 animate-spin" /> Loading models...
                    </p>
                  )}
                </div>

                {/* API key input */}
                {selectedProvider !== "ollama" ? (
                  <div>
                    <label className="mb-1.5 block text-xs font-medium text-muted-foreground">
                      API Key
                      {currentSettings?.has_api_key && currentSettings.provider === selectedProvider && (
                        <span className="ml-1.5 text-emerald-400">(saved)</span>
                      )}
                      {selectedProviderInfo?.configured_via_env && (
                        <span className="ml-1.5 text-amber-400">(env fallback)</span>
                      )}
                    </label>
                    <div className="relative">
                      <input
                        type={showApiKey ? "text" : "password"}
                        value={apiKey}
                        onChange={(e) => setApiKey(e.target.value)}
                        placeholder={
                          currentSettings?.has_api_key && currentSettings.provider === selectedProvider
                            ? "••••••••  (leave blank to keep)"
                            : "Enter your API key"
                        }
                        className="w-full rounded-lg border border-border/60 bg-background/60 px-3 py-2 pr-9 text-sm text-foreground placeholder:text-muted-foreground/50 focus:outline-none focus:ring-1 focus:ring-primary/50"
                      />
                      <button
                        type="button"
                        onClick={() => setShowApiKey(!showApiKey)}
                        className="absolute top-1/2 right-2.5 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                      >
                        {showApiKey ? <EyeOff className="h-3.5 w-3.5" /> : <Eye className="h-3.5 w-3.5" />}
                      </button>
                    </div>
                  </div>
                ) : (
                  <div>
                    <label className="mb-1.5 block text-xs font-medium text-muted-foreground">
                      Ollama Base URL
                    </label>
                    <input
                      type="text"
                      value={ollamaUrl}
                      onChange={(e) => setOllamaUrl(e.target.value)}
                      placeholder="http://localhost:11434"
                      className="w-full rounded-lg border border-border/60 bg-background/60 px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground/50 focus:outline-none focus:ring-1 focus:ring-primary/50"
                    />
                  </div>
                )}
              </div>

              {/* Temperature slider */}
              <div className="mt-3">
                <div className="mb-1.5 flex items-center justify-between">
                  <label className="flex items-center gap-1 text-xs font-medium text-muted-foreground">
                    <Thermometer className="h-3 w-3" />
                    Temperature
                  </label>
                  <span className="text-xs font-mono text-foreground">{temperature.toFixed(2)}</span>
                </div>
                <input
                  type="range"
                  min="0"
                  max="2"
                  step="0.05"
                  value={temperature}
                  onChange={(e) => setTemperature(parseFloat(e.target.value))}
                  className="w-full accent-primary"
                />
                <div className="flex justify-between text-[10px] text-muted-foreground">
                  <span>Precise</span>
                  <span>Creative</span>
                </div>
              </div>

              {/* Save / Reset */}
              <div className="mt-4 flex flex-wrap items-center gap-2">
                <Button
                  type="button"
                  size="sm"
                  className="gap-1.5"
                  onClick={handleSaveAi}
                  disabled={aiSaving}
                >
                  {aiSaving ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Save className="h-3.5 w-3.5" />}
                  Save Settings
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  className="gap-1.5"
                  onClick={handleResetAi}
                  disabled={aiSaving}
                >
                  <RotateCcw className="h-3.5 w-3.5" />
                  Reset to Defaults
                </Button>
              </div>

              {aiError && (
                <p className="mt-3 rounded-lg border border-rose-500/20 bg-rose-500/10 px-3 py-2 text-xs text-rose-400">
                  {aiError}
                </p>
              )}
              {aiSuccess && (
                <p className="mt-3 rounded-lg border border-emerald-500/20 bg-emerald-500/10 px-3 py-2 text-xs text-emerald-400">
                  {aiSuccess}
                </p>
              )}
            </div>
          </div>
        )}
      </section>

      {/* ── Google Calendar Integration ─────────────────────────────────── */}
      <section className="rounded-xl border border-border/40 bg-card/40 p-4 sm:rounded-2xl sm:p-5">
        <div className="mb-4 flex items-start gap-3">
          <div className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-primary/10 ring-1 ring-primary/20 sm:h-9 sm:w-9">
            <Calendar className="h-4 w-4 text-primary" />
          </div>
          <div className="min-w-0">
            <h2 className="text-base font-semibold text-foreground sm:text-lg">Google Calendar</h2>
            <p className="text-xs text-muted-foreground sm:text-sm">
              Check your OAuth token status and reconnect if expired. Tokens expire after 7 days if
              the app is in Google&apos;s Testing mode.
            </p>
          </div>
        </div>

        <div className="flex flex-col gap-3 rounded-xl border border-border/40 bg-background/40 px-3 py-3 sm:px-4">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex items-center gap-2 text-sm text-foreground">
              <StatusIcon
                className={cn("h-4 w-4 shrink-0", statusColor, statusSpin && "animate-spin")}
              />
              <span>
                Status:{" "}
                <span className={cn("font-semibold", statusColor)}>{statusText}</span>
              </span>
            </div>
            <div className="flex gap-2">
              <HeaderActionButton
                icon={RefreshCw}
                label="Re-check"
                loading={tokenChecking}
                onClick={checkToken}
                disabled={tokenChecking}
              />
              <HeaderActionButton
                icon={tokenConnecting ? Loader2 : Calendar}
                label={tokenHealth?.valid ? "Reconnect" : "Connect Google Calendar"}
                loading={tokenConnecting}
                onClick={handleReconnect}
                disabled={tokenConnecting || tokenChecking}
                active={needsReconnect}
              >
                {tokenHealth?.valid ? "Reconnect" : "Connect Google Calendar"}
              </HeaderActionButton>
            </div>
          </div>

          {tokenError && (
            <p className="rounded-lg border border-rose-500/20 bg-rose-500/10 px-3 py-2 text-xs text-rose-400">
              {tokenError}
            </p>
          )}
          {!tokenChecking && tokenHealth && !tokenHealth.valid && tokenHealth.reason && (
            <p className="rounded-lg border border-amber-500/20 bg-amber-500/10 px-3 py-2 text-xs text-amber-400">
              <span className="font-medium">Reason: </span>
              {tokenHealth.reason}
            </p>
          )}
          {!tokenChecking && tokenHealth?.valid && (
            <p className="text-xs text-muted-foreground">
              Your Google Calendar is connected. Events are synced automatically every 30 minutes.
            </p>
          )}
          {!tokenChecking && !tokenHealth?.connected && (
            <p className="text-xs text-muted-foreground">
              Connect your Google Calendar to enable AI-powered scheduling, event sync, and
              holiday/birthday visibility in the Calendar view.
            </p>
          )}
        </div>
      </section>

      {/* Slack Integration */}
      <section className="rounded-xl border border-border/40 bg-card/40 p-4 sm:rounded-2xl sm:p-5">
        <div className="mb-4 flex items-start gap-3">
          <div className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-primary/10 ring-1 ring-primary/20 sm:h-9 sm:w-9">
            <Slack className="h-4 w-4 text-primary" />
          </div>
          <div className="min-w-0">
            <h2 className="text-base font-semibold text-foreground sm:text-lg">Slack</h2>
            <p className="text-xs text-muted-foreground sm:text-sm">
              Connect or reconnect Slack so channels, messages, task actions, and team invites can
              use the latest workspace authorization.
            </p>
          </div>
        </div>

        <div className="flex flex-col gap-3 rounded-xl border border-border/40 bg-background/40 px-3 py-3 sm:px-4">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex flex-wrap items-center gap-2 text-sm text-foreground">
              <SlackStatusIcon
                className={cn("h-4 w-4 shrink-0", slackStatusColor, slackStatusSpin && "animate-spin")}
              />
              <span>
                Status:{" "}
                <span className={cn("font-semibold", slackStatusColor)}>{slackStatusText}</span>
              </span>
              {slackStatus?.team_name && (
                <span className="text-xs text-muted-foreground">
                  Workspace: {slackStatus.team_name}
                </span>
              )}
            </div>
            <div className="flex gap-2">
              <HeaderActionButton
                icon={RefreshCw}
                label="Re-check"
                loading={slackChecking}
                onClick={checkSlack}
                disabled={slackChecking || slackConnecting}
              />
              <HeaderActionButton
                icon={slackConnecting ? Loader2 : Slack}
                label={slackStatus?.connected ? "Reconnect Slack" : "Connect Slack"}
                loading={slackConnecting}
                onClick={handleSlackReconnect}
                disabled={slackConnecting || slackChecking}
                active={needsSlackReconnect}
              >
                {slackStatus?.connected ? "Reconnect Slack" : "Connect Slack"}
              </HeaderActionButton>
            </div>
          </div>

          {slackError && (
            <p className="rounded-lg border border-rose-500/20 bg-rose-500/10 px-3 py-2 text-xs text-rose-400">
              {slackError}
            </p>
          )}
          {!slackChecking && slackStatus?.connected && (
            <p className="text-xs text-muted-foreground">
              Slack is connected. Reconnect after changing Slack app scopes or reinstalling the app.
            </p>
          )}
          {!slackChecking && !slackStatus?.connected && (
            <p className="text-xs text-muted-foreground">
              Connect Slack from here after saving your Slack client ID, client secret, and bot token.
            </p>
          )}
        </div>
      </section>

      {/* ── AI Agent Toggle ────────────────────────────────────────────────── */}
      <section className="rounded-xl border border-border/40 bg-card/40 p-4 sm:rounded-2xl sm:p-5">
        <div className="mb-4 flex items-start gap-3">
          <div className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-primary/10 ring-1 ring-primary/20 sm:h-9 sm:w-9">
            <Bot className="h-4 w-4 text-primary" />
          </div>
          <div className="min-w-0">
            <h2 className="text-base font-semibold text-foreground sm:text-lg">AI Agent Toggle</h2>
            <p className="text-xs text-muted-foreground sm:text-sm">
              Turn agent features on or off without changing backend config.
            </p>
          </div>
        </div>

        <div className="flex flex-col gap-3 rounded-xl border border-border/40 bg-background/40 px-3 py-3 sm:flex-row sm:items-center sm:justify-between sm:px-4">
          <div className="text-sm text-foreground">
            Agent status:{" "}
            <span className={cn("font-semibold", aiEnabled ? "text-emerald-400" : "text-rose-400")}>
              {aiEnabled ? "Enabled" : "Disabled"}
            </span>
          </div>
          <HeaderActionButton
            icon={Bot}
            label={aiEnabled ? "Disable Agents" : "Enable Agents"}
            active={!aiEnabled}
            onClick={handleToggleAi}
            className="w-full justify-center sm:w-auto"
          >
            {aiEnabled ? "Disable Agents" : "Enable Agents"}
          </HeaderActionButton>
        </div>

        {/* Current active config summary */}
        {currentSettings && (
          <div className="mt-3 rounded-xl border border-border/40 bg-background/40 px-3 py-3 sm:px-4">
            <p className="text-xs text-muted-foreground">
              <span className="font-medium text-foreground">Active config:</span>{" "}
              <span className="text-primary">{currentSettings.provider}</span>{" "}
              / <span className="text-foreground">{currentSettings.model_id}</span>{" "}
              <span className="text-muted-foreground">
                (temp: {currentSettings.temperature.toFixed(2)})
              </span>
            </p>
          </div>
        )}
      </section>

      {/* ── Timeline Settings ──────────────────────────────────────────── */}
      <section className="rounded-xl border border-border/40 bg-card/40 p-4 sm:rounded-2xl sm:p-5">
        <div className="mb-4 flex items-start gap-3">
          <div className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-primary/10 ring-1 ring-primary/20 sm:h-9 sm:w-9">
            <Timer className="h-4 w-4 text-primary" />
          </div>
          <div className="min-w-0">
            <h2 className="text-base font-semibold text-foreground sm:text-lg">Timeline Settings</h2>
            <p className="text-xs text-muted-foreground sm:text-sm">
              Configure the day timeline on the Calendar page — update frequency, water reminders, and meal times.
            </p>
          </div>
        </div>

        <div className="space-y-4 rounded-xl border border-border/40 bg-background/40 p-3 sm:p-4">
          {/* Update interval */}
          <div>
            <label className="mb-1.5 block text-xs font-medium text-muted-foreground">Update Interval</label>
            <div className="relative">
              <select
                value={tlInterval}
                onChange={(e) => setTlInterval(Number(e.target.value))}
                className="h-11 w-full appearance-none rounded-lg border border-border/60 bg-background/60 px-3 pr-10 text-sm text-foreground [color-scheme:dark] focus:outline-none focus:ring-1 focus:ring-primary/50"
              >
                <option className="bg-popover text-popover-foreground" value={60000}>1 minute</option>
                <option className="bg-popover text-popover-foreground" value={120000}>2 minutes</option>
                <option className="bg-popover text-popover-foreground" value={300000}>5 minutes (default)</option>
                <option className="bg-popover text-popover-foreground" value={600000}>10 minutes</option>
                <option className="bg-popover text-popover-foreground" value={900000}>15 minutes</option>
              </select>
              <ChevronDown className="pointer-events-none absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            </div>
          </div>

          {/* Water reminders */}
          <div>
            <div className="mb-2 flex items-center justify-between">
              <label className="text-xs font-medium text-muted-foreground">Water Reminders</label>
              <button
                type="button"
                onClick={() => setTlWaterEnabled(!tlWaterEnabled)}
                className={cn(
                  "relative inline-flex h-5 w-9 shrink-0 items-center rounded-full border border-border/70 bg-background/70 transition-colors"
                )}
              >
                <span
                  className={cn(
                    "inline-block h-3.5 w-3.5 rounded-full transition-transform",
                    tlWaterEnabled ? "bg-emerald-400" : "bg-white",
                    tlWaterEnabled ? "translate-x-[18px]" : "translate-x-[3px]"
                  )}
                />
              </button>
            </div>
            {tlWaterEnabled && (
              <div className="grid grid-cols-3 gap-2">
                <div>
                  <label className="mb-1 block text-[10px] text-muted-foreground">Start Hour</label>
                  <input
                    type="text"
                    inputMode="numeric"
                    value={tlWaterStart}
                    onChange={(e) => setTlWaterStart(e.target.value)}
                    onBlur={() => setTlWaterStart(String(parseBoundedInput(tlWaterStart, 0, 24, 8)))}
                    className="w-full rounded-lg border border-border/60 bg-background/60 px-2 py-1.5 text-sm text-foreground [appearance:textfield] [color-scheme:dark] focus:outline-none focus:ring-1 focus:ring-primary/50 [&::-webkit-inner-spin-button]:appearance-none [&::-webkit-outer-spin-button]:appearance-none"
                  />
                </div>
                <div>
                  <label className="mb-1 block text-[10px] text-muted-foreground">End Hour</label>
                  <input
                    type="text"
                    inputMode="numeric"
                    value={tlWaterEnd}
                    onChange={(e) => setTlWaterEnd(e.target.value)}
                    onBlur={() => setTlWaterEnd(String(parseBoundedInput(tlWaterEnd, 0, 24, 22)))}
                    className="w-full rounded-lg border border-border/60 bg-background/60 px-2 py-1.5 text-sm text-foreground [appearance:textfield] [color-scheme:dark] focus:outline-none focus:ring-1 focus:ring-primary/50 [&::-webkit-inner-spin-button]:appearance-none [&::-webkit-outer-spin-button]:appearance-none"
                  />
                </div>
                <div>
                  <label className="mb-1 block text-[10px] text-muted-foreground">Step (min)</label>
                  <input
                    type="text"
                    inputMode="numeric"
                    value={tlWaterStep}
                    onChange={(e) => setTlWaterStep(e.target.value)}
                    onBlur={() => setTlWaterStep(String(parseBoundedInput(tlWaterStep, 1, 60, 60)))}
                    className="w-full rounded-lg border border-border/60 bg-background/60 px-2 py-1.5 text-sm text-foreground [appearance:textfield] [color-scheme:dark] focus:outline-none focus:ring-1 focus:ring-primary/50 [&::-webkit-inner-spin-button]:appearance-none [&::-webkit-outer-spin-button]:appearance-none"
                  />
                </div>
              </div>
            )}
          </div>

          {/* Meal times */}
          <div>
            <label className="mb-2 block text-xs font-medium text-muted-foreground">Meal Times</label>
            <div className="grid grid-cols-3 gap-2">
              <div>
                <label className="mb-1 block text-[10px] text-muted-foreground">Breakfast</label>
                <input
                  type="time"
                  value={tlBreakfast}
                  onChange={(e) => setTlBreakfast(e.target.value)}
                  className="w-full rounded-lg border border-border/60 bg-background/60 px-2 py-1.5 text-sm text-foreground [color-scheme:dark] focus:outline-none focus:ring-1 focus:ring-primary/50 [&::-webkit-calendar-picker-indicator]:invert"
                />
              </div>
              <div>
                <label className="mb-1 block text-[10px] text-muted-foreground">Lunch</label>
                <input
                  type="time"
                  value={tlLunch}
                  onChange={(e) => setTlLunch(e.target.value)}
                  className="w-full rounded-lg border border-border/60 bg-background/60 px-2 py-1.5 text-sm text-foreground [color-scheme:dark] focus:outline-none focus:ring-1 focus:ring-primary/50 [&::-webkit-calendar-picker-indicator]:invert"
                />
              </div>
              <div>
                <label className="mb-1 block text-[10px] text-muted-foreground">Dinner</label>
                <input
                  type="time"
                  value={tlDinner}
                  onChange={(e) => setTlDinner(e.target.value)}
                  className="w-full rounded-lg border border-border/60 bg-background/60 px-2 py-1.5 text-sm text-foreground [color-scheme:dark] focus:outline-none focus:ring-1 focus:ring-primary/50 [&::-webkit-calendar-picker-indicator]:invert"
                />
              </div>
            </div>
          </div>

          {/* Save button */}
          <div className="flex items-center gap-2">
            <Button type="button" size="sm" className="gap-1.5" onClick={handleSaveTimeline}>
              <Save className="h-3.5 w-3.5" />
              Save Timeline Settings
            </Button>
            {tlSaved && (
              <span className="text-xs text-emerald-400">Saved!</span>
            )}
          </div>
        </div>
      </section>

      {/* ── Integration Keys ────────────────────────────────────────────── */}
      <IntegrationKeysSection />
    </div>
  )
}

/* ─── Integration Keys Section ─────────────────────────────────────────────── */

interface IntegrationField {
  key: string
  label: string
  isSecret: boolean
}

interface IntegrationGroup {
  id: string
  label: string
  fields: IntegrationField[]
}

const INTEGRATION_GROUPS: IntegrationGroup[] = [
  {
    id: "google_fit",
    label: "Google Fit",
    fields: [
      { key: "google_fit_client_id", label: "Client ID", isSecret: true },
      { key: "google_fit_client_secret", label: "Client Secret", isSecret: true },
      { key: "google_fit_credentials_file", label: "Credentials File Path", isSecret: false },
      { key: "google_fit_token_file", label: "Token File Path", isSecret: false },
    ],
  },
  {
    id: "strava",
    label: "Strava",
    fields: [
      { key: "strava_client_id", label: "Client ID", isSecret: true },
      { key: "strava_client_secret", label: "Client Secret", isSecret: true },
      { key: "strava_refresh_token", label: "Refresh Token", isSecret: true },
      { key: "strava_token_file", label: "Token File Path", isSecret: false },
    ],
  },
  {
    id: "slack",
    label: "Slack",
    fields: [
      { key: "slack_client_id", label: "Client ID", isSecret: true },
      { key: "slack_client_secret", label: "Client Secret", isSecret: true },
      { key: "slack_bot_token", label: "Bot Token", isSecret: true },
    ],
  },
  {
    id: "github",
    label: "GitHub",
    fields: [
      { key: "github_client_id", label: "Client ID", isSecret: true },
      { key: "github_client_secret", label: "Client Secret", isSecret: true },
      { key: "github_oauth_redirect_uri", label: "OAuth Redirect URI", isSecret: false },
    ],
  },
  {
    id: "leetcode",
    label: "LeetCode",
    fields: [
      { key: "leetcode_username", label: "Username", isSecret: false },
    ],
  },
]

function IntegrationKeysSection() {
  const [keysStatus, setKeysStatus] = useState<Record<string, boolean>>({})
  const [values, setValues] = useState<Record<string, string>>({})
  const [visibility, setVisibility] = useState<Record<string, boolean>>({})
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const token = typeof window !== "undefined" ? localStorage.getItem("numa_token") : null
        const base = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"
        const res = await fetch(`${base}/api/ai-settings/integration-keys`, {
          headers: token ? { Authorization: `Bearer ${token}` } : {},
        })
        if (!res.ok) throw new Error("Failed to fetch integration key status")
        const data = await res.json()
        setKeysStatus(data)
        if (data.leetcode_username_value) {
          setValues((prev) => ({ ...prev, leetcode_username: data.leetcode_username_value }))
        }
        if (data.github_oauth_redirect_uri_value) {
          setValues((prev) => ({
            ...prev,
            github_oauth_redirect_uri: data.github_oauth_redirect_uri_value,
          }))
        }
        if (data.google_fit_credentials_file_value) {
          setValues((prev) => ({
            ...prev,
            google_fit_credentials_file: data.google_fit_credentials_file_value,
          }))
        }
        if (data.google_fit_token_file_value) {
          setValues((prev) => ({
            ...prev,
            google_fit_token_file: data.google_fit_token_file_value,
          }))
        }
        if (data.strava_token_file_value) {
          setValues((prev) => ({
            ...prev,
            strava_token_file: data.strava_token_file_value,
          }))
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load key status")
      } finally {
        setLoading(false)
      }
    }
    fetchStatus()
  }, [])

  const handleValueChange = (key: string, val: string) => {
    setValues((prev) => ({ ...prev, [key]: val }))
  }

  const toggleVisibility = (key: string) => {
    setVisibility((prev) => ({ ...prev, [key]: !prev[key] }))
  }

  const saveKeys = async (payload: Record<string, string>) => {
    setSaving(true)
    setError(null)
    setSuccess(null)
    try {
      const token = typeof window !== "undefined" ? localStorage.getItem("numa_token") : null
      const base = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"
      const res = await fetch(`${base}/api/ai-settings/integration-keys`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify(payload),
      })
      if (!res.ok) throw new Error("Failed to save integration keys")
      const data = await res.json()

      setKeysStatus((prev) => {
        const next = { ...prev }
        for (const k of data.updated || []) {
          next[k] = true
        }
        return next
      })

      if (payload.leetcode_username) {
        localStorage.setItem("numa_leetcode_username", payload.leetcode_username)
      }

      // Clear only the saved fields from values
      setValues((prev) => {
        const next = { ...prev }
        for (const k of data.updated || []) {
          delete next[k]
        }
        return next
      })
      setSuccess(`Saved ${(data.updated || []).length} key(s) successfully!`)
      setTimeout(() => setSuccess(null), 3000)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save keys")
      setTimeout(() => setError(null), 5000)
    } finally {
      setSaving(false)
    }
  }

  const handleSaveGroup = (group: IntegrationGroup) => {
    const payload: Record<string, string> = {}
    for (const field of group.fields) {
      const v = (values[field.key] ?? "").trim()
      if (v) payload[field.key] = v
    }
    if (Object.keys(payload).length === 0) {
      setError(`Enter at least one ${group.label} value to save.`)
      setTimeout(() => setError(null), 3000)
      return
    }
    void saveKeys(payload)
  }

  const handleSaveAll = () => {
    const payload: Record<string, string> = {}
    for (const [k, v] of Object.entries(values)) {
      if (v.trim()) payload[k] = v.trim()
    }
    if (Object.keys(payload).length === 0) {
      setError("Enter at least one value to save.")
      setTimeout(() => setError(null), 3000)
      return
    }
    void saveKeys(payload)
  }

  const isConfigured = (key: string) => keysStatus[key] ?? false

  return (
    <section className="rounded-xl border border-border/40 bg-card/40 p-4 sm:rounded-2xl sm:p-5">
      <div className="mb-4 flex items-start gap-3">
        <div className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-primary/10 ring-1 ring-primary/20 sm:h-9 sm:w-9">
          <Server className="h-4 w-4 text-primary" />
        </div>
        <div className="min-w-0">
          <h2 className="text-base font-semibold text-foreground sm:text-lg">Integration Keys</h2>
          <p className="text-xs text-muted-foreground sm:text-sm">
            Manage API keys for connected services. Keys are saved to the server&apos;s .env file.
            Leave fields blank to keep existing values.
          </p>
        </div>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-8">
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
        </div>
      ) : (
        <div className="space-y-4">
          {INTEGRATION_GROUPS.map((group) => (
            <div
              key={group.id}
              className="rounded-xl border border-border/40 bg-background/40 p-3 sm:p-4"
            >
              <h3 className="mb-3 text-sm font-semibold text-foreground">{group.label}</h3>
              <div className="space-y-2.5">
                {group.fields.map((field) => {
                  const configured = isConfigured(field.key)
                  const visible = visibility[field.key] ?? false
                  const val = values[field.key] ?? ""
                  return (
                    <div key={field.key}>
                      <label className="mb-1.5 flex items-center gap-1.5 text-xs font-medium text-muted-foreground">
                        <span
                          className={cn(
                            "inline-block h-2 w-2 rounded-full",
                            configured ? "bg-emerald-400" : "bg-rose-400"
                          )}
                        />
                        {field.label}
                        {configured && (
                          <span className="text-[10px] text-emerald-400/70">(configured)</span>
                        )}
                      </label>
                      <div className="relative">
                        <input
                          type={field.isSecret && !visible ? "password" : "text"}
                          value={val}
                          onChange={(e) => handleValueChange(field.key, e.target.value)}
                          placeholder={
                            configured
                              ? "••••••••  (configured, leave blank to keep)"
                              : "Enter value..."
                          }
                          className="w-full rounded-lg border border-border/60 bg-background/60 px-3 py-2 pr-9 text-sm text-foreground placeholder:text-muted-foreground/50 focus:outline-none focus:ring-1 focus:ring-primary/50"
                        />
                        {field.isSecret && (
                          <button
                            type="button"
                            onClick={() => toggleVisibility(field.key)}
                            className="absolute top-1/2 right-2.5 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                          >
                            {visible ? (
                              <EyeOff className="h-3.5 w-3.5" />
                            ) : (
                              <Eye className="h-3.5 w-3.5" />
                            )}
                          </button>
                        )}
                      </div>
                    </div>
                  )
                })}
              </div>
              <div className="mt-3 flex justify-end">
                <Button
                  type="button"
                  size="sm"
                  variant="outline"
                  className="gap-1.5 text-xs"
                  onClick={() => handleSaveGroup(group)}
                  disabled={saving}
                >
                  {saving ? (
                    <Loader2 className="h-3 w-3 animate-spin" />
                  ) : (
                    <Save className="h-3 w-3" />
                  )}
                  Save {group.label}
                </Button>
              </div>
            </div>
          ))}

          {/* Save All */}
          <div className="flex flex-wrap items-center gap-2">
            <Button
              type="button"
              size="sm"
              className="gap-1.5"
              onClick={handleSaveAll}
              disabled={saving}
            >
              {saving ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <Save className="h-3.5 w-3.5" />
              )}
              Save All Keys
            </Button>
          </div>

          {error && (
            <p className="rounded-lg border border-rose-500/20 bg-rose-500/10 px-3 py-2 text-xs text-rose-400">
              {error}
            </p>
          )}
          {success && (
            <p className="rounded-lg border border-emerald-500/20 bg-emerald-500/10 px-3 py-2 text-xs text-emerald-400">
              {success}
            </p>
          )}
        </div>
      )}
    </section>
  )
}
