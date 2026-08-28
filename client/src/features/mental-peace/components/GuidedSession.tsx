"use client"

import { ArrowLeft, ChevronLeft, ChevronRight, Pause, Play } from "lucide-react"
import { Button } from "@/components/ui/button"
import { YOGA_FLOW_AUDIO_SRC } from "../mentalPeace.constants"
import { formatClock, instructionForElapsed } from "../mentalPeace.utils"
import { useGuidedSession } from "../useGuidedSession"
import { BreathingGuide } from "./BreathingGuide"
import { GuidedPoseImage } from "./GuidedPoseImage"
import type { MoodType } from "../mentalPeace.types"

interface GuidedSessionProps {
  mood: MoodType
  onEnd: () => void
}

export function GuidedSession({ mood, onEnd }: GuidedSessionProps) {
  const {
    audioRef,
    poses,
    currentPose,
    currentIndex,
    isPlaying,
    timeRemaining,
    progress,
    togglePlay,
    goPrevious,
    goNext,
  } = useGuidedSession(mood, onEnd)

  return (
    <div className="flex h-dvh flex-col overflow-hidden bg-background">
      <audio ref={audioRef} src={YOGA_FLOW_AUDIO_SRC} preload="metadata" loop />

      <div className="flex items-center justify-between border-b border-border/40 p-4">
        <div className="flex items-center gap-4">
          <span className="text-sm text-muted-foreground">
            Pose {currentIndex + 1} of {poses.length}
          </span>
          <div className="h-1 w-32 overflow-hidden rounded-full bg-border/40">
            <div
              className="h-full rounded-full bg-primary transition-all duration-300"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>
        <button
          onClick={onEnd}
          className="inline-flex h-10 items-center gap-2 rounded-lg border border-border/40 bg-card/40 px-3 text-sm font-medium text-muted-foreground transition-colors hover:text-foreground"
        >
          <ArrowLeft className="h-4 w-4" />
          Back
        </button>
      </div>

      <div className="flex min-h-0 flex-1 flex-col overflow-hidden lg:flex-row">
        <div className="flex flex-col items-center justify-center p-4 sm:p-6 lg:w-1/2 lg:p-10">
          <div className="mb-8 w-full max-w-md" style={{ maxHeight: "350px" }}>
            <GuidedPoseImage pose={currentPose} />
          </div>
          <div className="mt-4">
            <BreathingGuide isActive={isPlaying} />
          </div>
        </div>

        <div className="flex flex-col justify-center p-4 sm:p-6 lg:w-1/2 lg:p-10">
          <div>
            <div className="mb-6">
              <div className="text-3xl font-light tabular-nums text-foreground sm:text-5xl">
                {formatClock(timeRemaining)}
              </div>
              <p className="mt-1 text-sm text-muted-foreground">
                Hold this pose
              </p>
            </div>

            <h2 className="text-xl font-bold text-foreground sm:text-2xl">
              {currentPose.englishName}
            </h2>
            <p className="mt-1 text-sm italic text-primary">
              {currentPose.sanskritName}
            </p>
            <p className="mb-6 text-xs text-muted-foreground">
              ({currentPose.pronunciation})
            </p>

            <div className="mb-6 rounded-2xl border border-border/40 bg-card/40 p-4">
              <p className="text-sm italic text-muted-foreground">
                &ldquo;{currentPose.moodReason}&rdquo;
              </p>
            </div>

            <div className="mb-8">
              <h4 className="mb-2 text-sm font-medium text-primary">
                Focus on:
              </h4>
              <p className="text-foreground leading-relaxed">
                {instructionForElapsed(currentPose.instructions, timeRemaining)}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <Button
              variant="outline"
              size="icon"
              onClick={goPrevious}
              disabled={currentIndex === 0}
            >
              <ChevronLeft className="h-5 w-5" />
            </Button>

            <Button onClick={togglePlay} className="flex-1 gap-2" size="lg">
              {isPlaying ? (
                <>
                  <Pause className="h-5 w-5" /> Pause
                </>
              ) : (
                <>
                  <Play className="h-5 w-5" /> Resume
                </>
              )}
            </Button>

            <Button variant="outline" size="icon" onClick={goNext}>
              <ChevronRight className="h-5 w-5" />
            </Button>
          </div>
        </div>
      </div>
    </div>
  )
}
