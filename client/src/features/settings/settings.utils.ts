/**
 * Settings helpers (NUMA-119 P5, PLAN 17.1 / 21.2).
 *
 * `clampInteger` and `parseBoundedInput` moved verbatim from
 * `settings/page.tsx`; the two status-label builders were the page's
 * `tokenStatusLabel`/`slackStatusLabel` closures, now pure functions of the
 * state they read. The AI kill-switch accessors from `lib/aiSettings.ts` landed
 * in `settings.storage.ts`, which stays import-free for the two feature APIs
 * that read it.
 */
import { AlertTriangle, CheckCircle2, Loader2, XCircle } from "lucide-react"

import type { TokenHealthResult } from "@/features/calendar/calendar.types"
import type { SlackStatus } from "@/features/slack/slack.types"
import { NON_SECRET_KEYS } from "./settings.constants"
import type { Bounds, ConnectionStatusLabel, IntegrationKeysStatus } from "./settings.types"

export function clampInteger(value: number, min: number, max: number, fallback: number): number {
  if (!Number.isFinite(value)) return fallback
  return Math.min(max, Math.max(min, Math.round(value)))
}

export function parseBoundedInput(
  value: string | number,
  min: number,
  max: number,
  fallback: number
): number {
  const parsed = typeof value === "number" ? value : Number.parseInt(value, 10)
  return clampInteger(parsed, min, max, fallback)
}

/** `parseBoundedInput` against one of the declared field bounds. */
export function clampToBounds(value: string | number, bounds: Bounds): number {
  return parseBoundedInput(value, bounds.min, bounds.max, bounds.fallback)
}

export function errorMessage(error: unknown, fallback: string): string {
  return error instanceof Error ? error.message : fallback
}

export function calendarStatusLabel(
  checking: boolean,
  health: TokenHealthResult | null
): ConnectionStatusLabel {
  if (checking) {
    return { text: "Checking…", color: "text-muted-foreground", Icon: Loader2, spin: true }
  }
  if (!health) {
    return { text: "Unknown", color: "text-muted-foreground", Icon: AlertTriangle, spin: false }
  }
  if (health.valid) {
    return { text: "Connected & valid", color: "text-emerald-400", Icon: CheckCircle2, spin: false }
  }
  if (health.connected) {
    return {
      text: "Token expired / revoked",
      color: "text-amber-400",
      Icon: AlertTriangle,
      spin: false,
    }
  }
  return { text: "Not connected", color: "text-rose-400", Icon: XCircle, spin: false }
}

export function slackStatusLabel(
  checking: boolean,
  status: SlackStatus | null
): ConnectionStatusLabel {
  if (checking) {
    return { text: "Checking...", color: "text-muted-foreground", Icon: Loader2, spin: true }
  }
  if (!status) {
    return { text: "Unknown", color: "text-muted-foreground", Icon: AlertTriangle, spin: false }
  }
  if (status.connected) {
    return { text: "Connected", color: "text-emerald-400", Icon: CheckCircle2, spin: false }
  }
  if (status.bot_configured) {
    return {
      text: "Bot token configured",
      color: "text-amber-400",
      Icon: AlertTriangle,
      spin: false,
    }
  }
  return { text: "Not connected", color: "text-rose-400", Icon: XCircle, spin: false }
}

/** Pull the `<key>_value` prefills the server echoes for the non-secret keys. */
export function prefillsFromStatus(status: IntegrationKeysStatus): Record<string, string> {
  const values: Record<string, string> = {}
  NON_SECRET_KEYS.forEach((key) => {
    const value = status[`${key}_value`]
    if (typeof value === "string" && value) values[key] = value
  })
  return values
}
