/**
 * Settings constants (NUMA-119 P5, PLAN 17.1 / 21.2).
 *
 * Provider presentation data, the integration-key groups and the timeline
 * bounds, extracted from the module-level tables and the inline JSX in
 * `settings/page.tsx`.
 */
import {
  DEFAULT_MEAL_TIMES,
  DEFAULT_TIMELINE_INTERVAL_MS,
  DEFAULT_WATER_CONFIG,
} from "@/features/calendar/calendar.constants"
import type { IntegrationGroup, MealFieldKey, TimelineForm } from "./settings.types"

export const DEFAULT_OLLAMA_URL = "http://localhost:11434"

export const DEFAULT_PROVIDER = "groq"

export const DEFAULT_TEMPERATURE = 0.1

/** Success/error banners clear themselves after these delays. */
export const AI_MESSAGE_TIMEOUT_MS = 3000
export const KEYS_SUCCESS_TIMEOUT_MS = 3000
export const KEYS_VALIDATION_TIMEOUT_MS = 3000
export const KEYS_SAVE_ERROR_TIMEOUT_MS = 5000
export const TIMELINE_SAVED_TIMEOUT_MS = 2500

export const PROVIDER_LOGOS: Record<string, string> = {
  groq: "groq.webp",
  openai: "openai.webp",
  anthropic: "anthropic.webp",
  gemini: "gemini.webp",
  ollama: "ollama.webp",
}

export const PROVIDER_DESCRIPTIONS: Record<string, string> = {
  groq: "Ultra-fast inference with Llama, Mixtral, and Gemma models",
  openai: "GPT-4o, GPT-4 Turbo, and GPT-3.5 models",
  anthropic: "Claude Sonnet, Haiku, and Opus models",
  gemini: "Google Gemini 2.0 Flash and Gemini 1.5 models",
  ollama: "Run local models on your machine - no API key needed",
}

/** Bounds the water-reminder inputs are clamped to on blur and on save. */
export const WATER_START_BOUNDS = { min: 0, max: 24, fallback: 8 } as const
export const WATER_END_BOUNDS = { min: 0, max: 24, fallback: 22 } as const
export const WATER_STEP_BOUNDS = { min: 1, max: 60, fallback: 60 } as const

export const TIMELINE_INTERVAL_OPTIONS = [
  { value: 60_000, label: "1 minute" },
  { value: 120_000, label: "2 minutes" },
  { value: 300_000, label: "5 minutes (default)" },
  { value: 600_000, label: "10 minutes" },
  { value: 900_000, label: "15 minutes" },
]

export const MEAL_FIELDS: { key: MealFieldKey; label: string }[] = [
  { key: "breakfast", label: "Breakfast" },
  { key: "lunch", label: "Lunch" },
  { key: "dinner", label: "Dinner" },
]

/** Timeline form defaults, taken from the calendar feature's own defaults. */
export const DEFAULT_TIMELINE_FORM: TimelineForm = {
  intervalMs: DEFAULT_TIMELINE_INTERVAL_MS,
  waterEnabled: true,
  waterStart: String(DEFAULT_WATER_CONFIG.startHour),
  waterEnd: String(DEFAULT_WATER_CONFIG.endHour),
  waterStep: String(DEFAULT_WATER_CONFIG.stepMinutes),
  breakfast: DEFAULT_MEAL_TIMES.breakfast,
  lunch: DEFAULT_MEAL_TIMES.lunch,
  dinner: DEFAULT_MEAL_TIMES.dinner,
}

export const INTEGRATION_GROUPS: IntegrationGroup[] = [
  {
    id: "google_fit",
    label: "Google Fit",
    fields: [
      { key: "google_fit_client_id", label: "Client ID", isSecret: true },
      { key: "google_fit_client_secret", label: "Client Secret", isSecret: true },
      { key: "google_fit_credentials_file", label: "Credentials File Path", isSecret: false },
      { key: "google_fit_token_file", label: "Token File Path", isSecret: false },
    ],
  },
  {
    id: "strava",
    label: "Strava",
    fields: [
      { key: "strava_client_id", label: "Client ID", isSecret: true },
      { key: "strava_client_secret", label: "Client Secret", isSecret: true },
      { key: "strava_refresh_token", label: "Refresh Token", isSecret: true },
      { key: "strava_token_file", label: "Token File Path", isSecret: false },
    ],
  },
  {
    id: "slack",
    label: "Slack",
    fields: [
      { key: "slack_client_id", label: "Client ID", isSecret: true },
      { key: "slack_client_secret", label: "Client Secret", isSecret: true },
      { key: "slack_bot_token", label: "Bot Token", isSecret: true },
    ],
  },
  {
    id: "github",
    label: "GitHub",
    fields: [
      { key: "github_client_id", label: "Client ID", isSecret: true },
      { key: "github_client_secret", label: "Client Secret", isSecret: true },
      { key: "github_oauth_redirect_uri", label: "OAuth Redirect URI", isSecret: false },
    ],
  },
  {
    id: "leetcode",
    label: "LeetCode",
    fields: [
      { key: "leetcode_username", label: "Username", isSecret: false },
    ],
  },
]

/**
 * Keys the server echoes back as `<key>_value`, so the form can prefill them.
 * Mirrors `NON_SECRET_KEYS` in `server/src/ai_settings/constants.py`.
 */
export const NON_SECRET_KEYS = [
  "leetcode_username",
  "github_oauth_redirect_uri",
  "google_fit_credentials_file",
  "google_fit_token_file",
  "strava_token_file",
]
