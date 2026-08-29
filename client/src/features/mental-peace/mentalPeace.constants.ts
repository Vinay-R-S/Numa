/**
 * Mental peace constants (NUMA-120 P4, PLAN 21.2).
 *
 * The magic numbers the session screens carried inline: stage ids, the mood
 * picker copy, the preparing-screen cadence, guided-session hold timings, the
 * meditation presets and the breath cycle. The soundscape catalog left on
 * NUMA-124: the player builds it from `/audio-library/ensure`.
 */
import { Angry, Annoyed, Bed, Frown, Meh, PersonStanding } from "lucide-react"
import { moodConfig } from "./data"
import type { BreathPhase, BreathPhaseConfig, MoodOption, MoodType, TimerPreset } from "./mentalPeace.types"

export const SESSION_STAGES = {
  ENTRY: 0,
  MOOD_SELECT: 1,
  PREPARING: 2,
  DASHBOARD: 3,
  GUIDED_SESSION: 4,
  MEDITATION: 5,
} as const

export type SessionStage = (typeof SESSION_STAGES)[keyof typeof SESSION_STAGES]

const YOGA_MOODS: { type: MoodType; description: string; icon: MoodOption["icon"] }[] = [
  { type: "overwhelmed", description: "Mind racing, too much happening", icon: Angry },
  { type: "low", description: "Lacking energy or motivation", icon: Frown },
  { type: "restless", description: "Can't settle, fidgety energy", icon: Annoyed },
  { type: "numb", description: "Feeling disconnected or flat", icon: Meh },
  { type: "exhausted", description: "Deeply tired, need restoration", icon: Bed },
]

/** Labels come from `moodConfig` so the picker cannot drift from the flows. */
export const MOOD_OPTIONS: MoodOption[] = [
  ...YOGA_MOODS.map((mood) => ({ ...mood, label: moodConfig[mood.type].label })),
  {
    type: "meditation",
    label: "Meditation",
    description: "Music, timer, and seated posture",
    icon: PersonStanding,
  },
]

export const PREPARING_MESSAGES = [
  "Preparing your space...",
  "Selecting poses for your mood...",
  "Creating your flow...",
  "Almost ready...",
]

export const PREPARING_MESSAGE_INTERVAL_MS = 700
export const PREPARING_DURATION_MS = 2800

/** Seconds held per pose, and how long one instruction stays on screen. */
export const POSE_HOLD_SECONDS = 30
export const INSTRUCTION_STEP_SECONDS = 6

export const YOGA_FLOW_AUDIO_SRC = "/api/audio/yoga-flow.ogg"
export const YOGA_FLOW_VOLUME = 0.28

/**
 * Placeholder rows drawn while the audio-library call is in flight. The catalog
 * itself lives on the server (NUMA-124, PLAN 10); this is only how tall the
 * list reserves, so it never has to match the real count exactly.
 */
export const SOUNDSCAPE_PLACEHOLDER_COUNT = 5

export const DEFAULT_PLAYER_VOLUME = 0.5
export const SEEK_STEP_SECONDS = 10

export const TIMER_PRESETS: TimerPreset[] = [
  { label: "5 min", seconds: 5 * 60 },
  { label: "10 min", seconds: 10 * 60 },
  { label: "15 min", seconds: 15 * 60 },
  { label: "20 min", seconds: 20 * 60 },
]

export const DEFAULT_TIMER_PRESET_INDEX = 1

/** Chime played when the meditation timer reaches zero. */
export const TIMER_COMPLETE_CHIME = {
  frequency: 528,
  peakGain: 0.1,
  durationSeconds: 2,
} as const

export const BREATH_PHASES: Record<BreathPhase, BreathPhaseConfig> = {
  inhale: { duration: 4000, label: "Inhale...", frequency: 396 },
  hold: { duration: 2000, label: "Hold...", frequency: 528 },
  exhale: { duration: 4000, label: "Exhale...", frequency: 417 },
}

export const BREATH_PHASE_SEQUENCE: BreathPhase[] = ["inhale", "hold", "exhale"]

/** Softer, slower-attack bell than the timer chime. */
export const BREATH_BELL = {
  peakGain: 0.08,
  attackSeconds: 0.1,
  durationSeconds: 1.5,
} as const

export const REFLECTION_PROMPTS = [
  "How does your body feel right now?",
  "What thoughts came up during your practice?",
  "What are you grateful for in this moment?",
  "Is there anything you want to let go of?",
]
