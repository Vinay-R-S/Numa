"use client"

import { Calendar, Loader2, RefreshCw } from "lucide-react"

import { HeaderActionButton } from "@/components/ui/header-action-button"

import type { UseCalendarConnectionReturn } from "../useCalendarConnection"
import { AlertMessage } from "./AlertMessage"
import { ConnectionStatusLine } from "./ConnectionStatusLine"
import { SettingsSection } from "./SettingsSection"

export function GoogleCalendarPanel({ calendar }: { calendar: UseCalendarConnectionReturn }) {
  const { health, checking, connecting, error, status } = calendar
  const connectLabel = health?.valid ? "Reconnect" : "Connect Google Calendar"

  return (
    <SettingsSection
      icon={Calendar}
      title="Google Calendar"
      description={
        <>
          Check your OAuth token status and reconnect if expired. Tokens expire after 7 days if
          the app is in Google&apos;s Testing mode.
        </>
      }
    >
      <div className="flex flex-col gap-3 rounded-xl border border-border/40 bg-background/40 px-3 py-3 sm:px-4">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <ConnectionStatusLine status={status} />
          <div className="flex gap-2">
            <HeaderActionButton
              icon={RefreshCw}
              label="Re-check"
              loading={checking}
              onClick={() => { void calendar.check() }}
              disabled={checking}
            />
            <HeaderActionButton
              icon={connecting ? Loader2 : Calendar}
              label={connectLabel}
              loading={connecting}
              onClick={() => { void calendar.reconnect() }}
              disabled={connecting || checking}
              active={calendar.needsReconnect}
            >
              {connectLabel}
            </HeaderActionButton>
          </div>
        </div>

        {error && <AlertMessage tone="error">{error}</AlertMessage>}

        {!checking && health && !health.valid && health.reason && (
          <AlertMessage tone="warning">
            <span className="font-medium">Reason: </span>
            {health.reason}
          </AlertMessage>
        )}

        {!checking && health?.valid && (
          <p className="text-xs text-muted-foreground">
            Your Google Calendar is connected. Events are synced automatically every 30 minutes.
          </p>
        )}

        {!checking && !health?.connected && (
          <p className="text-xs text-muted-foreground">
            Connect your Google Calendar to enable AI-powered scheduling, event sync, and
            holiday/birthday visibility in the Calendar view.
          </p>
        )}
      </div>
    </SettingsSection>
  )
}
