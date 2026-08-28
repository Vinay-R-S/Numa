"use client"

import { DEFAULT_OLLAMA_URL } from "../settings.constants"
import { SecretInput } from "./SecretInput"

/**
 * API key entry for the selected provider. The label states whether a key is
 * already stored for this provider and whether the server has an env fallback,
 * so a blank field is understood to mean "keep what is saved".
 */
export function ApiKeyField({
  value,
  revealed,
  hasSavedKey,
  envFallback,
  onChange,
  onToggleReveal,
}: {
  value: string
  revealed: boolean
  hasSavedKey: boolean
  envFallback: boolean
  onChange: (value: string) => void
  onToggleReveal: () => void
}) {
  return (
    <div>
      <label className="mb-1.5 block text-xs font-medium text-muted-foreground">
        API Key
        {hasSavedKey && <span className="ml-1.5 text-emerald-400">(saved)</span>}
        {envFallback && <span className="ml-1.5 text-amber-400">(env fallback)</span>}
      </label>
      <SecretInput
        value={value}
        revealed={revealed}
        placeholder={hasSavedKey ? "••••••••  (leave blank to keep)" : "Enter your API key"}
        onChange={onChange}
        onToggleReveal={onToggleReveal}
      />
    </div>
  )
}

/** Shown instead of the API key field: Ollama runs locally and needs no key. */
export function OllamaUrlField({
  value,
  onChange,
}: {
  value: string
  onChange: (value: string) => void
}) {
  return (
    <div>
      <label className="mb-1.5 block text-xs font-medium text-muted-foreground">
        Ollama Base URL
      </label>
      <input
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={DEFAULT_OLLAMA_URL}
        className="w-full rounded-lg border border-border/60 bg-background/60 px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground/50 focus:outline-none focus:ring-1 focus:ring-primary/50"
      />
    </div>
  )
}
