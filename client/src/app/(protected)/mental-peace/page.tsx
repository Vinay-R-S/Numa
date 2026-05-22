"use client"

import React, { useEffect, useState } from "react"
import { MoodType } from "./yogaData"
import { EntryScreen } from "./components/EntryScreen"
import { MoodSelector } from "./components/MoodSelector"
import { PreparingSession } from "./components/PreparingSession"
import { Dashboard } from "./components/Dashboard"
import { GuidedSession } from "./components/GuidedSession"
import { ReflectionCard } from "./components/ReflectionCard"

const STAGES = {
  ENTRY: 0,
  MOOD_SELECT: 1,
  PREPARING: 2,
  DASHBOARD: 3,
  GUIDED_SESSION: 4,
  REFLECTION: 5,
} as const

export default function MentalPeacePage() {
  const [stage, setStage] = useState<number>(STAGES.ENTRY)
  const [selectedMood, setSelectedMood] = useState<MoodType | null>(null)

  useEffect(() => {
    fetch("/api/audio-library/ensure", { method: "POST" }).catch(() => {
      // The player shows its own retry/error state if local audio is unavailable.
    })
  }, [])

  const handleMoodSelect = (mood: MoodType) => {
    setSelectedMood(mood)
    setStage(STAGES.PREPARING)
  }

  const handleReset = () => {
    setSelectedMood(null)
    setStage(STAGES.ENTRY)
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
              onEnd={() => setStage(STAGES.REFLECTION)}
            />
          </div>
        )
      case STAGES.REFLECTION:
        return <ReflectionCard onComplete={handleReset} />
      default:
        return null
    }
  }

  return (
    <div className="min-h-screen bg-background text-foreground overflow-hidden">
      {renderStage()}
    </div>
  )
}
