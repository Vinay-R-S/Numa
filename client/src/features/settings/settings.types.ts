/**
 * Settings feature contracts (NUMA-119 P5, PLAN 5.3 / 17.1 / 21.2).
 *
 * The AI provider types moved here verbatim from `lib/aiSettings.ts`; the
 * integration-key and status-label types were implicit in `settings/page.tsx`.
 */
import type { LucideIcon } from "lucide-react"

export type AiProvider = "groq" | "openai" | "anthropic" | "gemini" | "ollama"

export interface AiSettings {
  provider: AiProvider
  model_id: string
  has_api_key: boolean
  ollama_base_url?: string | null
  temperature: number
}

export interface ProviderInfo {
  id: AiProvider
  name: string
  configured_via_env: boolean
  models: string[]
  default_model: string
}

export interface ProvidersListResponse {
  providers: ProviderInfo[]
  current: AiSettings | null
}

export interface AiSettingsUpdate {
  provider: AiProvider
  model_id: string
  api_key?: string | null
  ollama_base_url?: string | null
  temperature?: number
}

/**
 * `/ai-settings/integration-keys` answers with one boolean per known key plus
 * a `<key>_value` string for each non-secret key, so the map is heterogeneous.
 */
export type IntegrationKeysStatus = Record<string, boolean | string>

export interface IntegrationKeysUpdateResult {
  ok: boolean
  updated: string[]
}

export interface IntegrationField {
  key: string
  label: string
  isSecret: boolean
}

export interface IntegrationGroup {
  id: string
  label: string
  fields: IntegrationField[]
}

/** Ollama's `/api/tags` payload; only the model names are read. */
export interface OllamaTagsResponse {
  models?: { name: string }[]
}

/** Rendered by the connection panels: label, tint and the icon to spin. */
export interface ConnectionStatusLabel {
  text: string
  color: string
  Icon: LucideIcon
  spin: boolean
}

/** Inclusive clamp for a numeric text field, with the value used when unparseable. */
export interface Bounds {
  min: number
  max: number
  fallback: number
}

/** The timeline form the settings panel edits before writing storage. */
export interface TimelineForm {
  intervalMs: number
  waterEnabled: boolean
  waterStart: string
  waterEnd: string
  waterStep: string
  breakfast: string
  lunch: string
  dinner: string
}

export type WaterFieldKey = "waterStart" | "waterEnd" | "waterStep"

export type MealFieldKey = "breakfast" | "lunch" | "dinner"
