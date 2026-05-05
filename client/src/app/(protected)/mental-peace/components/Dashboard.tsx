"use client"

import React, { useState } from "react"
import { ChevronDown } from "lucide-react"
import { MoodType, moodConfig } from "../yogaData"
import { MeditationTimer } from "./MeditationTimer"
import { MusicPlayer } from "./MusicPlayer"
import { YogaSection } from "./YogaSection"

interface DashboardProps {
  mood: MoodType
  onBeginSession: () => void
}

export function Dashboard({ mood, onBeginSession }: DashboardProps) {
  const [showWhyPoses, setShowWhyPoses] = useState(false)
  const config = moodConfig[mood]

  return (
    <div className="min-h-screen bg-background p-3 sm:p-6 lg:p-10">
      <div className="w-full">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-xl font-bold text-foreground sm:text-2xl">
            Your Session
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Take your time. Start with music, set a timer, or dive straight into the flow.
          </p>

          <div className="mt-4">
            <button
              onClick={() => setShowWhyPoses(!showWhyPoses)}
              className="flex items-center gap-1.5 text-sm text-muted-foreground transition-colors hover:text-foreground"
            >
              <span>Why these poses?</span>
              <ChevronDown
                className={`h-4 w-4 transition-transform duration-200 ${showWhyPoses ? "rotate-180" : ""}`}
              />
            </button>

            {showWhyPoses && (
              <p className="mt-3 max-w-2xl border-l-2 border-primary/30 pl-4 text-sm leading-relaxed text-muted-foreground">
                {config.therapeuticReason}
              </p>
            )}
          </div>
        </div>

        <div className="mb-8 h-px w-full bg-border/40" />

        {/* Main layout */}
        <div className="flex flex-col gap-4 sm:gap-6 lg:flex-row">
          <div className="lg:w-auto">
            <MusicPlayer />
          </div>

          <div className="min-w-0 flex-1">
            <YogaSection mood={mood} onBeginSession={onBeginSession} />
          </div>

          <div className="lg:w-auto">
            <MeditationTimer />
          </div>
        </div>
      </div>
    </div>
  )
}
