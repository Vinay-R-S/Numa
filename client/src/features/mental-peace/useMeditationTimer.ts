"use client"

/**
 * Meditation countdown (NUMA-120 P4, PLAN 21.2).
 *
 * The interval is rebuilt on every tick, exactly as the component's effect did
 * (`timeLeft` is a dependency). The completion chime now fires from the timer
 * callback instead of from inside a `setTimeLeft` updater, so React cannot
 * double-invoke it.
 */
import { useCallback, useEffect, useRef, useState } from "react"
import {
  DEFAULT_TIMER_PRESET_INDEX,
  TIMER_COMPLETE_CHIME,
  TIMER_PRESETS,
} from "./mentalPeace.constants"
import { playTone } from "./mentalPeace.utils"

const DEFAULT_SECONDS = TIMER_PRESETS[DEFAULT_TIMER_PRESET_INDEX].seconds

export interface UseMeditationTimerReturn {
  selectedTime: number
  timeLeft: number
  isRunning: boolean
  progress: number
  selectPreset: (seconds: number) => void
  toggleRunning: () => void
  reset: () => void
}

export function useMeditationTimer(): UseMeditationTimerReturn {
  const [selectedTime, setSelectedTime] = useState(DEFAULT_SECONDS)
  const [timeLeft, setTimeLeft] = useState(DEFAULT_SECONDS)
  const [isRunning, setIsRunning] = useState(false)
  const intervalRef = useRef<NodeJS.Timeout | null>(null)

  useEffect(() => {
    if (!isRunning || timeLeft <= 0) return undefined

    intervalRef.current = setInterval(() => {
      if (timeLeft > 1) {
        setTimeLeft(timeLeft - 1)
        return
      }

      setIsRunning(false)
      setTimeLeft(0)
      playTone(TIMER_COMPLETE_CHIME)
    }, 1000)

    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current)
    }
  }, [isRunning, timeLeft])

  const selectPreset = useCallback((seconds: number) => {
    setSelectedTime(seconds)
    setTimeLeft(seconds)
    setIsRunning(false)
  }, [])

  const reset = useCallback(() => {
    setTimeLeft(selectedTime)
    setIsRunning(false)
  }, [selectedTime])

  const toggleRunning = useCallback(() => setIsRunning((running) => !running), [])

  const progress = ((selectedTime - timeLeft) / selectedTime) * 100

  return { selectedTime, timeLeft, isRunning, progress, selectPreset, toggleRunning, reset }
}
