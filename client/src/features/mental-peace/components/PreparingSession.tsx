"use client"

import { useEffect, useState } from "react"
import { Loader2 } from "lucide-react"
import { moodConfig } from "../data"
import {
  PREPARING_DURATION_MS,
  PREPARING_MESSAGES,
  PREPARING_MESSAGE_INTERVAL_MS,
} from "../mentalPeace.constants"
import type { MoodType } from "../mentalPeace.types"

interface PreparingSessionProps {
  mood: MoodType
  onComplete: () => void
}

export function PreparingSession({ mood, onComplete }: PreparingSessionProps) {
  const [messageIndex, setMessageIndex] = useState(0)
  const config = moodConfig[mood]

  useEffect(() => {
    const messageInterval = setInterval(() => {
      setMessageIndex((prev) => (prev + 1) % PREPARING_MESSAGES.length)
    }, PREPARING_MESSAGE_INTERVAL_MS)

    const completeTimeout = setTimeout(onComplete, PREPARING_DURATION_MS)

    return () => {
      clearInterval(messageInterval)
      clearTimeout(completeTimeout)
    }
  }, [onComplete])

  return (
    <div className="flex h-full min-h-0 items-center justify-center bg-background px-4">
      <div className="max-w-md w-full rounded-2xl border border-border/40 bg-card/40 p-6 text-center sm:p-8">
        <Loader2 className="mx-auto mb-6 h-10 w-10 animate-spin text-primary" />

        <h2 className="text-xl font-bold text-foreground sm:text-2xl">
          {config.sequenceName}
        </h2>
        <p className="mt-1 text-sm text-muted-foreground">
          {config.flowSubtitle}
        </p>

        <p className="mt-6 text-sm text-muted-foreground">
          {PREPARING_MESSAGES[messageIndex]}
        </p>
      </div>
    </div>
  )
}
