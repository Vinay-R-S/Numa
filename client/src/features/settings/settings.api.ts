/**
 * Settings API (NUMA-119 P5, PLAN 17.5 / 21.2 / 22.2).
 *
 * Typed fetchers built on the shared `http` client, replacing
 * `lib/aiSettings.ts` (its own `API_BASE`/`getAuthHeaders` pair) and the two
 * raw `fetch` calls the integration-keys section ran inline. Per-endpoint
 * fallback error text is preserved through `errorMessage`; the backend
 * `{ detail }` still wins, so a save rejected for an unsupported model now
 * surfaces the server's message where the old code showed a status code.
 *
 * `getOllamaModels` deliberately stays on raw `fetch`: it talks to the user's
 * own Ollama host, not to NUMA, and `http` would attach the NUMA bearer token
 * to whatever URL is typed into the settings field.
 */
import { expectBody, http } from "@/lib/http"
import {
  integrationKeysStatusSchema,
  integrationKeysUpdateSchema,
  ollamaTagsSchema,
  aiSettingsSchema,
  providersListSchema,
} from "./settings.schema"
import type {
  AiSettings,
  AiSettingsUpdate,
  IntegrationKeysStatus,
  IntegrationKeysUpdateResult,
  ProvidersListResponse,
} from "./settings.types"

export function getAiSettings(): Promise<ProvidersListResponse> {
  const message = "Failed to fetch AI settings"
  return expectBody(
    http.get("/ai-settings", { schema: providersListSchema, errorMessage: message }),
    message
  )
}

export function updateAiSettings(body: AiSettingsUpdate): Promise<AiSettings> {
  const message = "Failed to update AI settings"
  return expectBody(
    http.put("/ai-settings", body, { schema: aiSettingsSchema, errorMessage: message }),
    message
  )
}

export function resetAiSettings(): Promise<void> {
  return http.del("/ai-settings", { errorMessage: "Failed to reset AI settings" })
}

export function getIntegrationKeysStatus(): Promise<IntegrationKeysStatus> {
  const message = "Failed to fetch integration key status"
  return expectBody(
    http.get("/ai-settings/integration-keys", {
      schema: integrationKeysStatusSchema,
      errorMessage: message,
    }),
    message
  )
}

export function updateIntegrationKeys(
  payload: Record<string, string>
): Promise<IntegrationKeysUpdateResult> {
  const message = "Failed to save integration keys"
  return expectBody(
    http.put("/ai-settings/integration-keys", payload, {
      schema: integrationKeysUpdateSchema,
      errorMessage: message,
    }),
    message
  )
}

export async function getOllamaModels(baseUrl: string): Promise<string[]> {
  const res = await fetch(`${baseUrl}/api/tags`)
  const data = ollamaTagsSchema.parse(await res.json())
  return (data.models || []).map((model) => model.name)
}
