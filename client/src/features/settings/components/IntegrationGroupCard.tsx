"use client"

import { Loader2, Save } from "lucide-react"

import { Button } from "@/components/ui/button"

import type { IntegrationGroup } from "../settings.types"
import type { UseIntegrationKeysReturn } from "../useIntegrationKeys"
import { IntegrationKeyField } from "./IntegrationKeyField"

/** One service's keys, with a save button that submits only that group. */
export function IntegrationGroupCard({
  group,
  keys,
}: {
  group: IntegrationGroup
  keys: UseIntegrationKeysReturn
}) {
  return (
    <div className="rounded-xl border border-border/40 bg-background/40 p-3 sm:p-4">
      <h3 className="mb-3 text-sm font-semibold text-foreground">{group.label}</h3>
      <div className="space-y-2.5">
        {group.fields.map((field) => (
          <IntegrationKeyField
            key={field.key}
            field={field}
            value={keys.values[field.key] ?? ""}
            configured={keys.isConfigured(field.key)}
            revealed={keys.isVisible(field.key)}
            onChange={(value) => keys.setValue(field.key, value)}
            onToggleReveal={() => keys.toggleVisibility(field.key)}
          />
        ))}
      </div>
      <div className="mt-3 flex justify-end">
        <Button
          type="button"
          size="sm"
          variant="outline"
          className="gap-1.5 text-xs"
          onClick={() => keys.saveGroup(group)}
          disabled={keys.saving}
        >
          {keys.saving ? (
            <Loader2 className="h-3 w-3 animate-spin" />
          ) : (
            <Save className="h-3 w-3" />
          )}
          Save {group.label}
        </Button>
      </div>
    </div>
  )
}
