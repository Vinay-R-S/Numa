"use client"

import { Loader2, Save, Server } from "lucide-react"

import { Button } from "@/components/ui/button"

import { INTEGRATION_GROUPS } from "../settings.constants"
import { useIntegrationKeys } from "../useIntegrationKeys"
import { AlertMessage } from "./AlertMessage"
import { IntegrationGroupCard } from "./IntegrationGroupCard"
import { SettingsSection } from "./SettingsSection"

/**
 * Server-side integration keys. Self-contained (its own hook instance) the way
 * `IntegrationKeysSection` was inside the page, since nothing else reads them.
 */
export function IntegrationKeysPanel() {
  const keys = useIntegrationKeys()

  return (
    <SettingsSection
      icon={Server}
      title="Integration Keys"
      description={
        <>
          Manage API keys for connected services. Keys are saved to the server&apos;s .env file.
          Leave fields blank to keep existing values.
        </>
      }
    >
      {keys.loading ? (
        <div className="flex items-center justify-center py-8">
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
        </div>
      ) : (
        <div className="space-y-4">
          {INTEGRATION_GROUPS.map((group) => (
            <IntegrationGroupCard key={group.id} group={group} keys={keys} />
          ))}

          <div className="flex flex-wrap items-center gap-2">
            <Button
              type="button"
              size="sm"
              className="gap-1.5"
              onClick={keys.saveAll}
              disabled={keys.saving}
            >
              {keys.saving ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <Save className="h-3.5 w-3.5" />
              )}
              Save All Keys
            </Button>
          </div>

          {keys.error && <AlertMessage tone="error">{keys.error}</AlertMessage>}
          {keys.success && <AlertMessage tone="success">{keys.success}</AlertMessage>}
        </div>
      )}
    </SettingsSection>
  )
}
