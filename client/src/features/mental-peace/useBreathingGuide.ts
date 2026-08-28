"use client"

/**
 * Breath cycle driver (NUMA-120 P4, PLAN 21.2).
 *
 * Inhale -> hold -> exhale on a timeout chain, one bell per phase. `phaseIndex`
 * is kept so the orb can be re-keyed and replay its animation on every cycle.
 */
import { useEffect, useState } from "react"
import { BREATH_BELL, BREATH_PHASES, BREATH_PHASE_SEQUENCE } from "./mentalPeace.constants"
import { playTone } from "./mentalPeace.utils"
import type { BreathPhase } from "./mentalPeace.types"

export interface UseBreathingGuideReturn {
  phase: BreathPhase
  phaseIndex: number
  label: string
}

export function useBreathingGuide(isActive: boolean): UseBreathingGuideReturn {
  const [phaseIndex, setPhaseIndex] = useState(0)
  const phase = BREATH_PHASE_SEQUENCE[phaseIndex]

  useEffect(() => {
    if (!isActive) return undefined

    playTone({ ...BREATH_BELL, frequency: BREATH_PHASES[phase].frequency })

    const timer = setTimeout(() => {
      setPhaseIndex((index) => (index + 1) % BREATH_PHASE_SEQUENCE.length)
    }, BREATH_PHASES[phase].duration)

    return () => clearTimeout(timer)
  }, [isActive, phase, phaseIndex])

  return { phase, phaseIndex, label: BREATH_PHASES[phase].label }
}
