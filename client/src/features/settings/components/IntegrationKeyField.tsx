"use client"

import { cn } from "@/lib/utils"

import type { IntegrationField } from "../settings.types"
import { SecretInput } from "./SecretInput"

/** One .env-backed key: a configured dot, the label and the value input. */
export function IntegrationKeyField({
  field,
  value,
  configured,
  revealed,
  onChange,
  onToggleReveal,
}: {
  field: IntegrationField
  value: string
  configured: boolean
  revealed: boolean
  onChange: (value: string) => void
  onToggleReveal: () => void
}) {
  return (
    <div>
      <label className="mb-1.5 flex items-center gap-1.5 text-xs font-medium text-muted-foreground">
        <span
          className={cn(
            "inline-block h-2 w-2 rounded-full",
            configured ? "bg-emerald-400" : "bg-rose-400"
          )}
        />
        {field.label}
        {configured && <span className="text-[10px] text-emerald-400/70">(configured)</span>}
      </label>
      <SecretInput
        value={value}
        secret={field.isSecret}
        revealed={revealed}
        placeholder={configured ? "••••••••  (configured, leave blank to keep)" : "Enter value..."}
        onChange={onChange}
        onToggleReveal={onToggleReveal}
      />
    </div>
  )
}
