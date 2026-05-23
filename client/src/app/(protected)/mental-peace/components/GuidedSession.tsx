"use client"

import React, { useState, useEffect, useRef } from "react"
import Image from "next/image"
import { ArrowLeft, ChevronLeft, ChevronRight, Play, Pause } from "lucide-react"
import { Button } from "@/components/ui/button"
import { MoodType, getPosesForMood, PoseWithMoodReason } from "../yogaData"
import { BreathingGuide } from "./BreathingGuide"

interface GuidedSessionProps {
  mood: MoodType
  onEnd: () => void
}

function GuidedPoseImage({ pose }: { pose: PoseWithMoodReason }) {
  const [imageError, setImageError] = useState(false)

  if (imageError) {
    return (
      <div className="flex h-full w-full items-center justify-center rounded-2xl border border-border/40 bg-card/40 p-8">
        <span className="text-center text-xl font-medium text-primary">
          {pose.englishName}
        </span>
      </div>
    )
  }

  return (
    <Image
      src={pose.imageUrl}
      alt={pose.englishName}
      width={900}
      height={520}
      unoptimized
      className="h-full w-full rounded-2xl object-contain"
      style={{ backgroundColor: "rgba(0,0,0,0.2)" }}
      onError={() => setImageError(true)}
    />
  )
}

export function GuidedSession({ mood, onEnd }: GuidedSessionProps) {
  const poses = getPosesForMood(mood)
  const [currentIndex, setCurrentIndex] = useState(0)
  const [isPlaying, setIsPlaying] = useState(true)
  const [timeRemaining, setTimeRemaining] = useState(30)
  const intervalRef = useRef<NodeJS.Timeout | null>(null)
  const yogaAudioRef = useRef<HTMLAudioElement | null>(null)

  const currentPose = poses[currentIndex]
  const progress = ((currentIndex + 1) / poses.length) * 100

  useEffect(() => {
    if (isPlaying && timeRemaining > 0) {
      intervalRef.current = setInterval(() => {
        setTimeRemaining((prev) => {
          if (prev <= 1) {
            if (currentIndex < poses.length - 1) {
              setCurrentIndex((i) => i + 1)
              return 30
            } else {
              setIsPlaying(false)
              onEnd()
              return 0
            }
          }
          return prev - 1
        })
      }, 1000)
    }

    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current)
    }
  }, [isPlaying, currentIndex, poses.length, onEnd, timeRemaining])

  useEffect(() => {
    const audio = yogaAudioRef.current
    if (!audio) return

    audio.volume = 0.28
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

  const handlePrevious = () => {
    if (currentIndex > 0) {
      setCurrentIndex(currentIndex - 1)
      setTimeRemaining(30)
    }
  }

  const handleNext = () => {
    if (currentIndex < poses.length - 1) {
      setCurrentIndex(currentIndex + 1)
      setTimeRemaining(30)
    } else {
      onEnd()
    }
  }

  return (
    <div className="flex h-dvh flex-col overflow-hidden bg-background">
      <audio
        ref={yogaAudioRef}
        src="/api/audio/yoga-flow.ogg"
        preload="metadata"
        loop
      />

      {/* Header */}
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

      {/* Main content */}
      <div className="flex min-h-0 flex-1 flex-col overflow-hidden lg:flex-row">
        {/* Left side - Pose Image and Breathing Guide */}
        <div className="flex flex-col items-center justify-center p-4 sm:p-6 lg:w-1/2 lg:p-10">
          <div className="mb-8 w-full max-w-md" style={{ maxHeight: "350px" }}>
            <GuidedPoseImage pose={currentPose} />
          </div>
          <div className="mt-4">
            <BreathingGuide isActive={isPlaying} />
          </div>
        </div>

        {/* Right side - Pose details */}
        <div className="flex flex-col justify-center p-4 sm:p-6 lg:w-1/2 lg:p-10">
          <div>
            {/* Timer */}
            <div className="mb-6">
              <div className="text-3xl font-light tabular-nums text-foreground sm:text-5xl">
                0:{timeRemaining.toString().padStart(2, "0")}
              </div>
              <p className="mt-1 text-sm text-muted-foreground">
                Hold this pose
              </p>
            </div>

            {/* Pose name */}
            <h2 className="text-xl font-bold text-foreground sm:text-2xl">
              {currentPose.englishName}
            </h2>
            <p className="mt-1 text-sm italic text-primary">
              {currentPose.sanskritName}
            </p>
            <p className="mb-6 text-xs text-muted-foreground">
              ({currentPose.pronunciation})
            </p>

            {/* Why this pose */}
            <div className="mb-6 rounded-2xl border border-border/40 bg-card/40 p-4">
              <p className="text-sm italic text-muted-foreground">
                &ldquo;{currentPose.moodReason}&rdquo;
              </p>
            </div>

            {/* Current instruction */}
            <div className="mb-8">
              <h4 className="mb-2 text-sm font-medium text-primary">
                Focus on:
              </h4>
              <p className="text-foreground leading-relaxed">
                {currentPose.instructions[Math.min(Math.floor((30 - timeRemaining) / 6), currentPose.instructions.length - 1)]}
              </p>
            </div>
          </div>

          {/* Controls */}
          <div className="flex items-center gap-3">
            <Button
              variant="outline"
              size="icon"
              onClick={handlePrevious}
              disabled={currentIndex === 0}
            >
              <ChevronLeft className="h-5 w-5" />
            </Button>

            <Button
              onClick={() => setIsPlaying(!isPlaying)}
              className="flex-1 gap-2"
              size="lg"
            >
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

            <Button
              variant="outline"
              size="icon"
              onClick={handleNext}
            >
              <ChevronRight className="h-5 w-5" />
            </Button>
          </div>
        </div>
      </div>
    </div>
  )
}
