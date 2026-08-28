"use client"

import { Bot } from "lucide-react"

import { HeaderActionButton } from "@/components/ui/header-action-button"
import { cn } from "@/lib/utils"

import type { AiSettings } from "../settings.types"
import { SettingsSection } from "./SettingsSection"

/**
 * Client-side agent kill switch plus a read-only summary of the config the
 * agents currently run on. The toggle is local storage only, so it never
 * touches the backend config.
 */
export function AgentTogglePanel({
  enabled,
  currentSettings,
  onToggle,
}: {
  enabled: boolean
  currentSettings: AiSettings | null
  onToggle: () => void
}) {
  const toggleLabel = enabled ? "Disable Agents" : "Enable Agents"

  return (
    <SettingsSection
      icon={Bot}
      title="AI Agent Toggle"
      description="Turn agent features on or off without changing backend config."
    >
      <div className="flex flex-col gap-3 rounded-xl border border-border/40 bg-background/40 px-3 py-3 sm:flex-row sm:items-center sm:justify-between sm:px-4">
        <div className="text-sm text-foreground">
          Agent status:{" "}
          <span className={cn("font-semibold", enabled ? "text-emerald-400" : "text-rose-400")}>
            {enabled ? "Enabled" : "Disabled"}
          </span>
        </div>
        <HeaderActionButton
          icon={Bot}
          label={toggleLabel}
          active={!enabled}
          onClick={onToggle}
          className="w-full justify-center sm:w-auto"
        >
          {toggleLabel}
        </HeaderActionButton>
      </div>

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
    </SettingsSection>
  )
}
