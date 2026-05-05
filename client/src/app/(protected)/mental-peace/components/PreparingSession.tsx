"use client"

import React, { useEffect, useState } from "react"
import { Loader2 } from "lucide-react"
import { MoodType, moodConfig } from "../yogaData"

interface PreparingSessionProps {
  mood: MoodType
  onComplete: () => void
}

const preparingMessages = [
  "Preparing your space...",
  "Selecting poses for your mood...",
  "Creating your flow...",
  "Almost ready...",
]

export function PreparingSession({ mood, onComplete }: PreparingSessionProps) {
  const [messageIndex, setMessageIndex] = useState(0)
  const config = moodConfig[mood]

  useEffect(() => {
    const messageInterval = setInterval(() => {
      setMessageIndex((prev) => (prev + 1) % preparingMessages.length)
    }, 700)

    const completeTimeout = setTimeout(() => {
      onComplete()
    }, 2800)

    return () => {
      clearInterval(messageInterval)
      clearTimeout(completeTimeout)
    }
  }, [onComplete])

  return (
    <div className="min-h-screen flex items-center justify-center bg-background px-4">
      <div className="max-w-md w-full rounded-2xl border border-border/40 bg-card/40 p-6 text-center sm:p-8">
        <Loader2 className="mx-auto mb-6 h-10 w-10 animate-spin text-primary" />

        <h2 className="text-xl font-bold text-foreground sm:text-2xl">
          {config.sequenceName}
        </h2>
        <p className="mt-1 text-sm text-muted-foreground">
          {config.flowSubtitle}
        </p>

        <p className="mt-6 text-sm text-muted-foreground">
          {preparingMessages[messageIndex]}
        </p>
      </div>
    </div>
  )
}
