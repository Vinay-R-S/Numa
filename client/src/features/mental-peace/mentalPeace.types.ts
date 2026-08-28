/**
 * Mental peace domain types (NUMA-120 P4, PLAN 5.3 / 21.2).
 *
 * Split out of `app/(protected)/mental-peace/yogaData.ts`, which mixed the
 * types, the pose database and the mood-to-pose mapping in one file.
 */
import type { LucideIcon } from "lucide-react"

export type MoodType = "overwhelmed" | "low" | "restless" | "numb" | "exhausted"

/** Mood picker entry: the five yoga moods plus the standalone meditation flow. */
export type MoodChoice = MoodType | "meditation"

export interface YogaPose {
  id: string
  englishName: string
  sanskritName: string
  pronunciation: string
  imageUrl: string
  /** 1-5, rendered as filled dots. */
  difficulty: number
  duration: string
  instructions: string[]
  benefits: string
}

export interface PoseWithMoodReason extends YogaPose {
  moodReason: string
}

export interface MoodPoseEntry {
  poseId: string
  moodReason: string
}

export interface MoodConfig {
  label: string
  color: string
  gradient: string
  sequenceName: string
  flowSubtitle: string
  therapeuticReason: string
  poses: MoodPoseEntry[]
}

export interface MoodOption {
  type: MoodChoice
  label: string
  description: string
  icon: LucideIcon
}

export interface Soundscape {
  id: string
  name: string
  description: string
  src: string
  /** Used until the audio element reports a real duration. */
  fallbackDuration: number
}

export type BreathPhase = "inhale" | "hold" | "exhale"

export interface BreathPhaseConfig {
  duration: number
  label: string
  frequency: number
}

export interface TimerPreset {
  label: string
  seconds: number
}

export interface AudioLibraryItem {
  id: string
  kind: string
  label: string
  filename: string
  duration_seconds: number
  url: string
  ready: boolean
}

export interface AudioLibraryFailure {
  id: string
  detail: string
}

export interface AudioLibraryEnsureResult {
  ok: boolean
  downloaded: string[]
  failed: AudioLibraryFailure[]
  items: AudioLibraryItem[]
}
