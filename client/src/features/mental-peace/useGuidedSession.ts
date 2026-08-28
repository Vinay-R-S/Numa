"use client"

/**
 * Guided yoga flow state (NUMA-120 P4, PLAN 21.2).
 *
 * Pose cursor, the per-pose countdown and the looping ambience the session
 * plays underneath. Advancing and ending now happen in the interval callback
 * rather than inside a `setTimeRemaining` updater; the tick cadence, the reset
 * to a full hold on every pose change and the end-of-flow exit are unchanged.
 */
import { useCallback, useEffect, useMemo, useRef, useState } from "react"
import { POSE_HOLD_SECONDS, YOGA_FLOW_VOLUME } from "./mentalPeace.constants"
import { getPosesForMood } from "./mentalPeace.utils"
import type { MoodType, PoseWithMoodReason } from "./mentalPeace.types"
import type { RefObject } from "react"

export interface UseGuidedSessionReturn {
  audioRef: RefObject<HTMLAudioElement | null>
  poses: PoseWithMoodReason[]
  currentPose: PoseWithMoodReason
  currentIndex: number
  isPlaying: boolean
  timeRemaining: number
  progress: number
  togglePlay: () => void
  goPrevious: () => void
  goNext: () => void
}

export function useGuidedSession(mood: MoodType, onEnd: () => void): UseGuidedSessionReturn {
  const poses = useMemo(() => getPosesForMood(mood), [mood])
  const [currentIndex, setCurrentIndex] = useState(0)
  const [isPlaying, setIsPlaying] = useState(true)
  const [timeRemaining, setTimeRemaining] = useState(POSE_HOLD_SECONDS)
  const intervalRef = useRef<NodeJS.Timeout | null>(null)
  const audioRef = useRef<HTMLAudioElement | null>(null)

  useEffect(() => {
    if (!isPlaying || timeRemaining <= 0) return undefined

    intervalRef.current = setInterval(() => {
      if (timeRemaining > 1) {
        setTimeRemaining(timeRemaining - 1)
        return
      }

      if (currentIndex < poses.length - 1) {
        setCurrentIndex(currentIndex + 1)
        setTimeRemaining(POSE_HOLD_SECONDS)
        return
      }

      setIsPlaying(false)
      setTimeRemaining(0)
      onEnd()
    }, 1000)

    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current)
    }
  }, [isPlaying, currentIndex, poses.length, onEnd, timeRemaining])

  useEffect(() => {
    const audio = audioRef.current
    if (!audio) return undefined

    audio.volume = YOGA_FLOW_VOLUME
    audio.loop = true

    if (isPlaying) {
      audio.play().catch(() => {
        // Session controls continue normally if the browser blocks audio.
      })
    } else {
      audio.pause()
    }

    return () => {
      audio.pause()
    }
  }, [isPlaying])

  const goPrevious = useCallback(() => {
    if (currentIndex === 0) return

    setCurrentIndex(currentIndex - 1)
    setTimeRemaining(POSE_HOLD_SECONDS)
  }, [currentIndex])

  const goNext = useCallback(() => {
    if (currentIndex >= poses.length - 1) {
      onEnd()
      return
    }

    setCurrentIndex(currentIndex + 1)
    setTimeRemaining(POSE_HOLD_SECONDS)
  }, [currentIndex, onEnd, poses.length])

  const togglePlay = useCallback(() => setIsPlaying((playing) => !playing), [])

  return {
    audioRef,
    poses,
    currentPose: poses[currentIndex],
    currentIndex,
    isPlaying,
    timeRemaining,
    progress: ((currentIndex + 1) / poses.length) * 100,
    togglePlay,
    goPrevious,
    goNext,
  }
}
