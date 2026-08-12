/**
 * Health validation schemas (NUMA-116 P4, PLAN 22.2 / 22.3).
 *
 * Mirrors the Pydantic DTOs in `server/src/health_agent/schemas.py`. Response
 * schemas run through the shared `http` `schema` option so contract drift fails
 * loudly instead of rendering `undefined`; the input schema mirrors
 * `HealthChatRequest` for the agent composer.
 *
 * Date and timestamp fields stay strings: the backend serializes `date` /
 * `datetime` and the UI formats them itself, so structure is validated without
 * coercing values. Every metric is `nullable` rather than `nullish` because the
 * response models always emit the key, null-valued when a provider had no data.
 */
import { z } from "@/lib/validation"
import type {
  HealthChatResponse,
  HealthIntraday,
  HealthIntradayBucket,
  HealthSnapshot,
  HealthStatus,
  HealthSyncAllResult,
  HealthSyncResult,
} from "./health.types"

/** Google Fit reports stage hours as numbers; unknown stages are kept as-is. */
const sleepStagesSchema = z.looseObject({
  deep: z.number().optional(),
  light: z.number().optional(),
  rem: z.number().optional(),
  generic: z.number().optional(),
})

/** Google Fit: activity name -> session count. Strava: a list of activities. */
const activitiesSchema = z.union([
  z.record(z.string(), z.number()),
  z.array(z.record(z.string(), z.unknown())),
])

/**
 * The three JSONB pass-through columns degrade to null instead of rejecting the
 * response. The server types them `Any` / `Dict[str, Any]` and stores whatever a
 * provider wrote, so a shape this schema does not model is a real possibility;
 * failing the parse would take the whole 8-day snapshot list with it and blank
 * the dashboard over fields the UI either never reads (`activities`,
 * `sleep_stages`) or already re-validates itself (`normalizeSleepSegments`
 * filters junk segments). Metrics that are actually rendered stay strict, so
 * genuine contract drift still fails loudly (PLAN 22.2).
 */
const sleepStagesField = sleepStagesSchema.nullable().catch(null)
const activitiesField = activitiesSchema.nullable().catch(null)
const sleepSegmentsField = z.array(z.record(z.string(), z.unknown())).nullish().catch(null)

export const healthSnapshotSchema: z.ZodType<HealthSnapshot> = z.object({
  id: z.string(),
  user_id: z.string(),
  source: z.string(),
  snapshot_date: z.string(),
  steps: z.number().nullable(),
  active_minutes: z.number().nullable(),
  calories: z.number().nullable(),
  distance_km: z.number().nullable(),
  sleep_hours: z.number().nullable(),
  heart_rate_bpm: z.number().nullable(),
  heart_points: z.number().nullable(),
  sleep_start_at: z.string().nullish(),
  sleep_end_at: z.string().nullish(),
  sleep_stages: sleepStagesField,
  sleep_segments: sleepSegmentsField,
  activities: activitiesField,
  created_at: z.string().nullish(),
  updated_at: z.string().nullish(),
})

export const healthSnapshotListSchema = z.array(healthSnapshotSchema)

export const healthIntradayBucketSchema: z.ZodType<HealthIntradayBucket> = z.object({
  bucket_start_at: z.string().nullish(),
  bucket_end_at: z.string().nullish(),
  label: z.string(),
  range_label: z.string(),
  steps: z.number(),
  calories: z.number(),
  distance_km: z.number(),
})

export const healthIntradaySchema: z.ZodType<HealthIntraday> = z.object({
  id: z.string().nullish(),
  user_id: z.string(),
  source: z.string(),
  snapshot_date: z.string(),
  window_start_at: z.string(),
  window_end_at: z.string(),
  bucket_minutes: z.number(),
  steps: z.number(),
  calories: z.number(),
  distance_km: z.number(),
  buckets: z.array(healthIntradayBucketSchema),
  created_at: z.string().nullish(),
  updated_at: z.string().nullish(),
})

export const healthStatusSchema: z.ZodType<HealthStatus> = z.object({
  google_fit_configured: z.boolean(),
  strava_configured: z.boolean(),
  snapshots_today: z.number(),
  total_snapshots: z.number(),
})

/**
 * Loose: `/sync/google-fit` and `/sync/strava` answer through `HealthSyncOut`,
 * but the same dicts also ride inside `/sync/all`, which has no `response_model`
 * and so keeps the sync layer's extra flags (`sleep_synced`, `hourly_synced`,
 * `transient`, `not_connected`). A strict object would silently drop them.
 */
export const healthSyncResultSchema: z.ZodType<HealthSyncResult> = z.looseObject({
  ok: z.boolean(),
  source: z.string(),
  snapshot_date: z.string().nullish(),
  detail: z.string().nullish(),
})

/**
 * `/sync/all` has no `response_model`, so the route returns the raw dict from
 * `HealthService.sync_all`: the roll-up plus the per-provider result lists.
 */
export const healthSyncAllResultSchema: z.ZodType<HealthSyncAllResult> = z.looseObject({
  ok: z.boolean(),
  detail: z.string().nullish(),
  google_fit: z.array(healthSyncResultSchema).optional(),
  strava: z.array(healthSyncResultSchema).optional(),
})

export const healthChatResponseSchema: z.ZodType<HealthChatResponse> = z.object({
  response: z.string(),
  success: z.boolean(),
  delegated_to: z.string().nullish(),
  refresh_health: z.boolean().optional(),
})

/** Input schema for the agent composer; mirrors `HealthChatRequest`. */
export const healthChatRequestSchema = z.object({
  query: z.string().trim().min(1),
})

export type HealthChatInput = z.infer<typeof healthChatRequestSchema>
