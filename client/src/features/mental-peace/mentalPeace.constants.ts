/**
 * Mental peace constants (NUMA-120 P4, PLAN 21.2).
 *
 * The magic numbers the session screens carried inline: stage ids, the mood
 * picker copy, the preparing-screen cadence, guided-session hold timings, the
 * soundscape catalog, the meditation presets and the breath cycle.
 */
import { Angry, Annoyed, Bed, Frown, Meh, PersonStanding } from "lucide-react"
import { moodConfig } from "./data"
import type { BreathPhase, BreathPhaseConfig, MoodOption, MoodType, Soundscape, TimerPreset } from "./mentalPeace.types"

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

export const SOUNDSCAPES: Soundscape[] = [
  {
    id: "rain-thunder-birds",
    name: "Rain and Birds",
    description: "Rainfall with soft thunder and birds",
    src: "/api/audio/rain-thunder-birds.ogg",
    fallbackDuration: 134,
  },
  {
    id: "forest-ambience",
    name: "Forest Ambience",
    description: "Forest wind, birds, and insects",
    src: "/api/audio/forest-ambience.ogg",
    fallbackDuration: 123,
  },
  {
    id: "ocean-waves",
    name: "Ocean Waves",
    description: "Waves rolling over small stones",
    src: "/api/audio/ocean-waves.ogg",
    fallbackDuration: 120,
  },
  {
    id: "water-on-rocks",
    name: "Water on Rocks",
    description: "Shore water breaking on rocks",
    src: "/api/audio/water-on-rocks.ogg",
    fallbackDuration: 155,
  },
  {
    id: "yoga-flow",
    name: "Yoga Flow",
    description: "Layered forest and water ambience",
    src: "/api/audio/yoga-flow.ogg",
    fallbackDuration: 123,
  },
]

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
