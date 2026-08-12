/**
 * Health domain types (NUMA-116 P4, PLAN 5.3 / 21.2).
 *
 * The API DTOs mirror the response models in `server/src/health_agent/schemas.py`
 * and moved here unchanged from `components/health/healthApi.ts`. The view types
 * below them came from `health/page.tsx`.
 */

export interface HealthAgentMessage {
  role: "user" | "assistant"
  content: string
}

export interface HealthChatResponse {
  response: string
  success: boolean
  delegated_to?: string | null
  refresh_health?: boolean
}

export interface HealthSnapshot {
  id: string
  user_id: string
  source: string
  snapshot_date: string
  steps: number | null
  active_minutes: number | null
  calories: number | null
  distance_km: number | null
  sleep_hours: number | null
  heart_rate_bpm: number | null
  heart_points: number | null
  sleep_start_at?: string | null
  sleep_end_at?: string | null
  sleep_stages: { deep?: number; light?: number; rem?: number; generic?: number } | null
  sleep_segments?: Array<Record<string, unknown>> | null
  activities: Record<string, number> | Array<Record<string, unknown>> | null
  created_at?: string | null
  updated_at?: string | null
}

export interface HealthIntradayBucket {
  bucket_start_at?: string | null
  bucket_end_at?: string | null
  label: string
  range_label: string
  steps: number
  calories: number
  distance_km: number
}

export interface HealthIntraday {
  id?: string | null
  user_id: string
  source: string
  snapshot_date: string
  window_start_at: string
  window_end_at: string
  bucket_minutes: number
  steps: number
  calories: number
  distance_km: number
  buckets: HealthIntradayBucket[]
  created_at?: string | null
  updated_at?: string | null
}

export interface HealthStatus {
  google_fit_configured: boolean
  strava_configured: boolean
  snapshots_today: number
  total_snapshots: number
}

export interface HealthSyncResult {
  ok: boolean
  source: string
  snapshot_date?: string | null
  detail?: string | null
}

export interface HealthSyncAllResult {
  ok: boolean
  detail?: string | null
  google_fit?: HealthSyncResult[]
  strava?: HealthSyncResult[]
}

/** Metric plotted by the activity chart; also a `HealthSnapshot` numeric key. */
export type WeeklyActivityMetric = "steps" | "calories" | "distance_km"

/** Activity chart window: the selected day's hourly buckets or the last 7 days. */
export type ActivityChartMode = "day" | "week"

export type SleepStage = "generic" | "light" | "deep" | "rem"

export interface SleepTimelineSegment {
  startMs: number
  endMs: number
  stage: SleepStage
  hours: number
}

/** One point of the activity chart, ready to render. */
export interface ActivityChartPoint {
  date: string
  label: string
  range?: string
  value: number
  displayValue: string
}
