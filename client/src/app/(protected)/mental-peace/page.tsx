"use client"

import React, { useEffect, useState } from "react"
import { ArrowLeft, Leaf } from "lucide-react"
import { HeaderActionButton } from "@/components/ui/header-action-button"
import { MoodType } from "./yogaData"
import { EntryScreen } from "./components/EntryScreen"
import { MoodSelector } from "./components/MoodSelector"
import { PreparingSession } from "./components/PreparingSession"
import { Dashboard } from "./components/Dashboard"
import { GuidedSession } from "./components/GuidedSession"
import { MeditationSession } from "./components/MeditationSession"

const STAGES = {
  ENTRY: 0,
  MOOD_SELECT: 1,
  PREPARING: 2,
  DASHBOARD: 3,
  GUIDED_SESSION: 4,
  MEDITATION: 5,
} as const

export default function MentalPeacePage() {
  const [stage, setStage] = useState<number>(STAGES.ENTRY)
  const [selectedMood, setSelectedMood] = useState<MoodType | null>(null)

  useEffect(() => {
    fetch("/api/audio-library/ensure", { method: "POST" }).catch(() => {
      // The player shows its own retry/error state if local audio is unavailable.
    })
  }, [])

  const handleMoodSelect = (mood: MoodType | "meditation") => {
    if (mood === "meditation") {
      setSelectedMood(null)
      setStage(STAGES.MEDITATION)
      return
    }

    setSelectedMood(mood)
    setStage(STAGES.PREPARING)
  }

  const handleBack = () => {
    if (stage === STAGES.MOOD_SELECT) {
      setStage(STAGES.ENTRY)
      return
    }

    if (stage === STAGES.PREPARING || stage === STAGES.DASHBOARD || stage === STAGES.MEDITATION) {
      setSelectedMood(null)
      setStage(STAGES.MOOD_SELECT)
    }
  }

  const renderStage = () => {
    switch (stage) {
      case STAGES.ENTRY:
        return <EntryScreen onBegin={() => setStage(STAGES.MOOD_SELECT)} />
      case STAGES.MOOD_SELECT:
        return <MoodSelector onSelect={handleMoodSelect} />
      case STAGES.PREPARING:
        return (
          <PreparingSession
            mood={selectedMood!}
            onComplete={() => setStage(STAGES.DASHBOARD)}
          />
        )
      case STAGES.DASHBOARD:
        return (
          <Dashboard
            mood={selectedMood!}
            onBeginSession={() => setStage(STAGES.GUIDED_SESSION)}
          />
        )
      case STAGES.GUIDED_SESSION:
        return (
          <div className="fixed inset-0 z-50">
            <GuidedSession
              mood={selectedMood!}
              onEnd={() => setStage(STAGES.DASHBOARD)}
            />
          </div>
        )
      case STAGES.MEDITATION:
        return <MeditationSession />
      default:
        return null
    }
  }

  return (
    <div className="flex h-full w-full flex-col gap-4 overflow-hidden bg-background px-4 py-4 text-foreground sm:px-6 sm:py-6">
      {stage !== STAGES.GUIDED_SESSION && (
        <header className="flex shrink-0 flex-col gap-3 rounded-2xl border border-border/40 bg-card/40 p-4 sm:flex-row sm:items-center sm:justify-between sm:p-5">
          <div className="flex items-center gap-3">
            <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-muted/30 ring-1 ring-border/50">
              <Leaf className="h-5 w-5 text-foreground" />
            </div>
            <div>
              <h1 className="text-xl font-bold tracking-tight text-foreground sm:text-2xl">
                Mental Peace
              </h1>
              <p className="text-xs text-muted-foreground sm:text-sm">
                Stillness, breath, and guided recovery
              </p>
            </div>
          </div>
          {stage !== STAGES.ENTRY && (
            <HeaderActionButton
              icon={ArrowLeft}
              label="Back"
              onClick={handleBack}
            />
          )}
        </header>
      )}
      <div className="min-h-0 flex-1">
        {renderStage()}
      </div>
    </div>
  )
}
