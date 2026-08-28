"use client"

import { useState } from "react"
import { ChevronDown } from "lucide-react"
import { moodConfig } from "../data"
import { MeditationTimer } from "./MeditationTimer"
import { MusicPlayer } from "./MusicPlayer"
import { YogaSection } from "./YogaSection"
import type { MoodType } from "../mentalPeace.types"

interface SessionDashboardProps {
  mood: MoodType
  onBeginSession: () => void
}

export function SessionDashboard({ mood, onBeginSession }: SessionDashboardProps) {
  const [showWhyPoses, setShowWhyPoses] = useState(false)
  const config = moodConfig[mood]

  return (
    <div className="h-full overflow-hidden bg-background p-3 sm:p-4 lg:p-5">
      <div className="flex h-full w-full flex-col">
        <div className="mb-4 shrink-0">
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

        <div className="mb-4 h-px w-full shrink-0 bg-border/40" />

        <div className="flex min-h-0 flex-1 flex-col gap-4 overflow-hidden sm:gap-5 lg:flex-row">
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
