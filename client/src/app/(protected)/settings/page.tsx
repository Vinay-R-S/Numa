"use client"

import { useCallback, useEffect, useState } from "react"
import { Bot, Cpu, Sparkles, Calendar, CheckCircle2, XCircle, RefreshCw, AlertTriangle, Loader2 } from "lucide-react"

import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import { AiModelPreset, getAiSettings, setAiSettings } from "@/lib/aiSettings"
import {
  checkCalendarTokenHealth,
  getGoogleCalendarAuthorizationUrl,
  TokenHealthResult,
} from "@/components/calendar/api"

export default function SettingsPage() {
  const [enabled, setEnabled] = useState(() => getAiSettings().enabled)
  const [modelPreset, setModelPreset] = useState<AiModelPreset>(() => getAiSettings().modelPreset)

  // ── Google Calendar token state ────────────────────────────────────────────
  const [tokenHealth, setTokenHealth] = useState<TokenHealthResult | null>(null)
  const [tokenChecking, setTokenChecking] = useState(false)
  const [tokenConnecting, setTokenConnecting] = useState(false)
  const [tokenError, setTokenError] = useState<string | null>(null)

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

  // Check on mount
  useEffect(() => {
    checkToken()
  }, [checkToken])

  const handleReconnect = async () => {
    // If health check already returned a reconnect_url, use it directly
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

  // ── AI settings ─────────────────────────────────────────────────────────────
  const handleToggleAi = () => {
    const updated = setAiSettings({ enabled: !enabled })
    setEnabled(updated.enabled)
  }

  const handleModelChange = (preset: AiModelPreset) => {
    const updated = setAiSettings({ modelPreset: preset })
    setModelPreset(updated.modelPreset)
  }

  // ── Token status display helpers ───────────────────────────────────────────
  const tokenStatusLabel = () => {
    if (tokenChecking) return { text: "Checking…", color: "text-muted-foreground", Icon: Loader2, spin: true }
    if (!tokenHealth) return { text: "Unknown", color: "text-muted-foreground", Icon: AlertTriangle, spin: false }
    if (tokenHealth.valid) return { text: "Connected & valid", color: "text-emerald-400", Icon: CheckCircle2, spin: false }
    if (tokenHealth.connected) return { text: "Token expired / revoked", color: "text-amber-400", Icon: AlertTriangle, spin: false }
    return { text: "Not connected", color: "text-rose-400", Icon: XCircle, spin: false }
  }

  const { text: statusText, color: statusColor, Icon: StatusIcon, spin: statusSpin } = tokenStatusLabel()
  const needsReconnect = !tokenChecking && tokenHealth !== null && !tokenHealth.valid

  return (
    <div className="mx-auto flex min-h-full w-full max-w-5xl flex-col gap-4 px-3 py-4 sm:gap-6 sm:px-6 sm:py-6">
      <header className="rounded-xl border border-border/40 bg-card/40 p-4 sm:rounded-2xl sm:p-5">
        <h1 className="text-xl font-bold tracking-tight text-foreground sm:text-2xl">Settings</h1>
        <p className="mt-1 text-xs text-muted-foreground sm:text-sm">
          Configure AI agent behavior, model presets, and integrations.
        </p>
      </header>

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
          {/* Status row */}
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
              <Button
                type="button"
                variant="outline"
                size="sm"
                className="gap-1.5"
                onClick={checkToken}
                disabled={tokenChecking}
              >
                <RefreshCw className={cn("h-3.5 w-3.5", tokenChecking && "animate-spin")} />
                Re-check
              </Button>

              <Button
                type="button"
                size="sm"
                className="gap-1.5"
                onClick={handleReconnect}
                disabled={tokenConnecting || tokenChecking}
                variant={needsReconnect ? "default" : "outline"}
              >
                {tokenConnecting ? (
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                ) : (
                  <Calendar className="h-3.5 w-3.5" />
                )}
                {tokenHealth?.valid ? "Reconnect" : "Connect Google Calendar"}
              </Button>
            </div>
          </div>

          {/* Error message */}
          {tokenError && (
            <p className="rounded-lg border border-rose-500/20 bg-rose-500/10 px-3 py-2 text-xs text-rose-400">
              {tokenError}
            </p>
          )}

          {/* Expiry reason when token is bad */}
          {!tokenChecking && tokenHealth && !tokenHealth.valid && tokenHealth.reason && (
            <p className="rounded-lg border border-amber-500/20 bg-amber-500/10 px-3 py-2 text-xs text-amber-400">
              <span className="font-medium">Reason: </span>
              {tokenHealth.reason}
            </p>
          )}

          {/* Info note */}
          {!tokenChecking && tokenHealth?.valid && (
            <p className="text-xs text-muted-foreground">
              ✓ Your Google Calendar is connected. Events are synced automatically every 30 minutes.
              Click &quot;Reconnect&quot; if you want to reauthorise with a different Google account.
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
            <span className={cn("font-semibold", enabled ? "text-emerald-400" : "text-rose-400")}>
              {enabled ? "Enabled" : "Disabled"}
            </span>
          </div>
          <Button
            type="button"
            variant={enabled ? "outline" : "default"}
            size="sm"
            className="w-full sm:w-auto"
            onClick={handleToggleAi}
          >
            {enabled ? "Disable Agents" : "Enable Agents"}
          </Button>
        </div>
      </section>

      {/* ── Groq Model Preset ─────────────────────────────────────────────── */}
      <section className="rounded-xl border border-border/40 bg-card/40 p-4 sm:rounded-2xl sm:p-5">
        <div className="mb-4 flex items-start gap-3">
          <div className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-primary/10 ring-1 ring-primary/20 sm:h-9 sm:w-9">
            <Cpu className="h-4 w-4 text-primary" />
          </div>
          <div className="min-w-0">
            <h2 className="text-base font-semibold text-foreground sm:text-lg">Groq Model Preset</h2>
            <p className="text-xs text-muted-foreground sm:text-sm">
              Choose the default inference size used by Calendar and Master Agent chats.
            </p>
          </div>
        </div>

        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <button
            type="button"
            onClick={() => handleModelChange("70b")}
            className={cn(
              "rounded-xl border px-3 py-3 text-left transition-all sm:px-4 sm:py-4",
              modelPreset === "70b"
                ? "border-primary/50 bg-primary/10 ring-1 ring-primary/30"
                : "border-border/40 bg-background/40 hover:bg-accent/40"
            )}
          >
            <div className="mb-1 flex items-center gap-2 text-foreground">
              <Sparkles className="h-4 w-4 text-primary" />
              <span className="font-semibold">70B</span>
            </div>
            <p className="text-xs text-muted-foreground sm:text-sm">Higher quality reasoning, slower and costlier.</p>
          </button>

          <button
            type="button"
            onClick={() => handleModelChange("8b")}
            className={cn(
              "rounded-xl border px-3 py-3 text-left transition-all sm:px-4 sm:py-4",
              modelPreset === "8b"
                ? "border-primary/50 bg-primary/10 ring-1 ring-primary/30"
                : "border-border/40 bg-background/40 hover:bg-accent/40"
            )}
          >
            <div className="mb-1 flex items-center gap-2 text-foreground">
              <Sparkles className="h-4 w-4 text-primary" />
              <span className="font-semibold">8B</span>
            </div>
            <p className="text-xs text-muted-foreground sm:text-sm">Faster responses and lower cost for lightweight tasks.</p>
          </button>
        </div>
      </section>
    </div>
  )
}
