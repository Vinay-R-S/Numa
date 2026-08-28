"use client"

/**
 * Mental peace stage machine (NUMA-120 P4, PLAN 21.2).
 *
 * Owns the page's stage/mood state and the best-effort audio prewarm the page
 * ran inline, so `page.tsx` is composition only.
 */
import { useCallback, useEffect, useState } from "react"
import { ensureAudioLibrary } from "./mentalPeace.api"
import { SESSION_STAGES, type SessionStage } from "./mentalPeace.constants"
import type { MoodChoice, MoodType } from "./mentalPeace.types"

export interface UseMentalPeaceSessionReturn {
  stage: SessionStage
  selectedMood: MoodType | null
  begin: () => void
  selectMood: (mood: MoodChoice) => void
  startGuidedSession: () => void
  finishPreparing: () => void
  endGuidedSession: () => void
  goBack: () => void
}

export function useMentalPeaceSession(): UseMentalPeaceSessionReturn {
  const [stage, setStage] = useState<SessionStage>(SESSION_STAGES.ENTRY)
  const [selectedMood, setSelectedMood] = useState<MoodType | null>(null)

  useEffect(() => {
    // Warms the download while the user picks a mood; the player shows its own
    // retry/error state if local audio is unavailable.
    ensureAudioLibrary().catch(() => {
      // Best effort: the player retries and reports its own error state.
    })
  }, [])

  const selectMood = useCallback((mood: MoodChoice) => {
    if (mood === "meditation") {
      setSelectedMood(null)
      setStage(SESSION_STAGES.MEDITATION)
      return
    }

    setSelectedMood(mood)
    setStage(SESSION_STAGES.PREPARING)
  }, [])

  const goBack = useCallback(() => {
    if (stage === SESSION_STAGES.MOOD_SELECT) {
      setStage(SESSION_STAGES.ENTRY)
      return
    }

    if (
      stage === SESSION_STAGES.PREPARING ||
      stage === SESSION_STAGES.DASHBOARD ||
      stage === SESSION_STAGES.MEDITATION
    ) {
      setSelectedMood(null)
      setStage(SESSION_STAGES.MOOD_SELECT)
    }
  }, [stage])

  const begin = useCallback(() => setStage(SESSION_STAGES.MOOD_SELECT), [])
  const finishPreparing = useCallback(() => setStage(SESSION_STAGES.DASHBOARD), [])
  const startGuidedSession = useCallback(() => setStage(SESSION_STAGES.GUIDED_SESSION), [])
  const endGuidedSession = useCallback(() => setStage(SESSION_STAGES.DASHBOARD), [])

  return {
    stage,
    selectedMood,
    begin,
    selectMood,
    startGuidedSession,
    finishPreparing,
    endGuidedSession,
    goBack,
  }
}
