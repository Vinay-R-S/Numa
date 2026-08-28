/**
 * Mental peace pure helpers (NUMA-120 P4, PLAN 21.2).
 *
 * `getPosesForMood` / `getAllUniquePoses` moved here from `yogaData.ts`;
 * `formatClock` and `playTone` collapse helpers that were copied per component
 * (`formatTime` in the music player and the meditation timer, the WebAudio
 * bell in the breathing guide and the timer).
 */
import { moodConfig, yogaPoses } from "./data"
import { INSTRUCTION_STEP_SECONDS, POSE_HOLD_SECONDS } from "./mentalPeace.constants"
import type { MoodType, PoseWithMoodReason, YogaPose } from "./mentalPeace.types"

export function getPosesForMood(mood: MoodType): PoseWithMoodReason[] {
  return moodConfig[mood].poses.map((entry) => ({
    ...yogaPoses[entry.poseId],
    moodReason: entry.moodReason,
  }))
}

/** Every pose referenced by at least one mood, de-duplicated. */
export function getAllUniquePoses(): YogaPose[] {
  const uniqueIds = new Set<string>()
  Object.values(moodConfig).forEach((config) => {
    config.poses.forEach((entry) => uniqueIds.add(entry.poseId))
  })
  return Array.from(uniqueIds).map((id) => yogaPoses[id])
}

/** m:ss, for elapsed/remaining readouts. */
export function formatClock(seconds: number): string {
  const safeSeconds = Number.isFinite(seconds) ? Math.max(0, seconds) : 0
  const minutes = Math.floor(safeSeconds / 60)
  const rest = Math.floor(safeSeconds % 60)
  return `${minutes}:${rest.toString().padStart(2, "0")}`
}

/** mm:ss, for the meditation countdown. */
export function formatCountdown(seconds: number): string {
  const safeSeconds = Number.isFinite(seconds) ? Math.max(0, seconds) : 0
  const minutes = Math.floor(safeSeconds / 60)
  const rest = Math.floor(safeSeconds % 60)
  return `${minutes.toString().padStart(2, "0")}:${rest.toString().padStart(2, "0")}`
}

/** Instruction shown for the elapsed part of a pose hold, clamped to the last one. */
export function instructionForElapsed(instructions: string[], secondsRemaining: number): string {
  const elapsed = POSE_HOLD_SECONDS - secondsRemaining
  const index = Math.min(Math.floor(elapsed / INSTRUCTION_STEP_SECONDS), instructions.length - 1)
  return instructions[index]
}

export interface ToneOptions {
  frequency: number
  peakGain: number
  /** Fade-in length; 0 starts at full gain like the timer chime did. */
  attackSeconds?: number
  durationSeconds: number
}

/**
 * Plays a single sine bell through a short-lived AudioContext.
 *
 * The context is closed once the tone has decayed; the timer chime used to
 * leave one open per completed session.
 */
export function playTone({ frequency, peakGain, attackSeconds = 0, durationSeconds }: ToneOptions): void {
  if (typeof window === "undefined") return

  const AudioContextClass =
    window.AudioContext || (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext
  if (!AudioContextClass) return

  try {
    const ctx = new AudioContextClass()
    const oscillator = ctx.createOscillator()
    const gain = ctx.createGain()

    oscillator.connect(gain)
    gain.connect(ctx.destination)
    oscillator.type = "sine"
    oscillator.frequency.setValueAtTime(frequency, ctx.currentTime)

    if (attackSeconds > 0) {
      gain.gain.setValueAtTime(0, ctx.currentTime)
      gain.gain.linearRampToValueAtTime(peakGain, ctx.currentTime + attackSeconds)
    } else {
      gain.gain.setValueAtTime(peakGain, ctx.currentTime)
    }
    gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + durationSeconds)

    oscillator.start(ctx.currentTime)
    oscillator.stop(ctx.currentTime + durationSeconds)

    setTimeout(() => {
      void ctx.close().catch(() => {
        // Context already closed by the browser; nothing to release.
      })
    }, (durationSeconds + 0.5) * 1000)
  } catch {
    // WebAudio blocked or unavailable; the session continues silently.
  }
}
