/**
 * Settings validation schemas (NUMA-119 P5, PLAN 22.2 / 22.3).
 *
 * Mirrors the Pydantic DTOs in `server/src/ai_settings/schemas.py`. Response
 * schemas run through the shared `http` `schema` option, so contract drift
 * fails loudly instead of rendering `undefined`.
 *
 * The provider enum is the same five ids as `PROVIDER_MODELS` in
 * `server/src/core/llm_factory.py`; it is an enum rather than a bare string
 * because the whole UI (logos, descriptions, the ollama branch) is keyed by it.
 * The integration-keys map has no `response_model` server-side: it is a dict of
 * one boolean per known key plus a `<key>_value` string per non-secret key, so
 * it validates as a record of that union rather than a fixed object.
 */
import { z } from "@/lib/validation"
import type {
  AiProvider,
  AiSettings,
  IntegrationKeysStatus,
  IntegrationKeysUpdateResult,
  OllamaTagsResponse,
  ProviderInfo,
  ProvidersListResponse,
} from "./settings.types"

export const aiProviderSchema: z.ZodType<AiProvider> = z.enum([
  "groq",
  "openai",
  "anthropic",
  "gemini",
  "ollama",
])

export const aiSettingsSchema: z.ZodType<AiSettings> = z.object({
  provider: aiProviderSchema,
  model_id: z.string(),
  has_api_key: z.boolean(),
  ollama_base_url: z.string().nullish(),
  temperature: z.number(),
})

export const providerInfoSchema: z.ZodType<ProviderInfo> = z.object({
  id: aiProviderSchema,
  name: z.string(),
  configured_via_env: z.boolean(),
  models: z.array(z.string()),
  default_model: z.string(),
})

export const providersListSchema: z.ZodType<ProvidersListResponse> = z.object({
  providers: z.array(providerInfoSchema),
  current: aiSettingsSchema.nullable(),
})

export const integrationKeysStatusSchema: z.ZodType<IntegrationKeysStatus> = z.record(
  z.string(),
  z.union([z.boolean(), z.string()])
)

export const integrationKeysUpdateSchema: z.ZodType<IntegrationKeysUpdateResult> = z.object({
  ok: z.boolean(),
  updated: z.array(z.string()),
})

/** Ollama is a third-party service, so only the field the UI reads is required. */
export const ollamaTagsSchema: z.ZodType<OllamaTagsResponse> = z.looseObject({
  models: z.array(z.looseObject({ name: z.string() })).optional(),
})

/**
 * Mirrors `AISettingsUpdate` for the form layer (PLAN 22.3 contract parity), the
 * way `tasks.schema.ts` and `journal.schema.ts` carry their input schemas. The
 * PUT itself is not gated on it: the panel constrains provider, model and
 * temperature through the picker and the slider, and the server's message for
 * an out-of-range value reads better than a zod issue would.
 */
export const aiSettingsUpdateSchema = z.object({
  provider: aiProviderSchema,
  model_id: z.string().min(1),
  api_key: z.string().nullish(),
  ollama_base_url: z.string().nullish(),
  temperature: z.number().min(0).max(2),
})
