"use client"

import { Loader2, RefreshCw, Slack } from "lucide-react"

import { HeaderActionButton } from "@/components/ui/header-action-button"

import type { UseSlackConnectionReturn } from "../useSlackConnection"
import { AlertMessage } from "./AlertMessage"
import { ConnectionStatusLine } from "./ConnectionStatusLine"
import { SettingsSection } from "./SettingsSection"

export function SlackPanel({ slack }: { slack: UseSlackConnectionReturn }) {
  const { status, checking, connecting, error, statusLabel } = slack
  const connectLabel = status?.connected ? "Reconnect Slack" : "Connect Slack"

  return (
    <SettingsSection
      icon={Slack}
      title="Slack"
      description="Connect or reconnect Slack so channels, messages, task actions, and team invites can use the latest workspace authorization."
    >
      <div className="flex flex-col gap-3 rounded-xl border border-border/40 bg-background/40 px-3 py-3 sm:px-4">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <ConnectionStatusLine status={statusLabel} className="flex-wrap">
            {status?.team_name && (
              <span className="text-xs text-muted-foreground">Workspace: {status.team_name}</span>
            )}
          </ConnectionStatusLine>
          <div className="flex gap-2">
            <HeaderActionButton
              icon={RefreshCw}
              label="Re-check"
              loading={checking}
              onClick={() => { void slack.check() }}
              disabled={checking || connecting}
            />
            <HeaderActionButton
              icon={connecting ? Loader2 : Slack}
              label={connectLabel}
              loading={connecting}
              onClick={() => { void slack.reconnect() }}
              disabled={connecting || checking}
              active={slack.needsReconnect}
            >
              {connectLabel}
            </HeaderActionButton>
          </div>
        </div>

        {error && <AlertMessage tone="error">{error}</AlertMessage>}

        {!checking && status?.connected && (
          <p className="text-xs text-muted-foreground">
            Slack is connected. Reconnect after changing Slack app scopes or reinstalling the app.
          </p>
        )}

        {!checking && !status?.connected && (
          <p className="text-xs text-muted-foreground">
            Connect Slack from here after saving your Slack client ID, client secret, and bot token.
          </p>
        )}
      </div>
    </SettingsSection>
  )
}
