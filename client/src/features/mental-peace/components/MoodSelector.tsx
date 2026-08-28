"use client"

import { MOOD_OPTIONS } from "../mentalPeace.constants"
import { MoodCard } from "./MoodCard"
import type { MoodChoice } from "../mentalPeace.types"

interface MoodSelectorProps {
  onSelect: (mood: MoodChoice) => void
}

export function MoodSelector({ onSelect }: MoodSelectorProps) {
  return (
    <div className="flex h-full min-h-0 items-center justify-center bg-background px-4 py-6 sm:py-8">
      <div className="w-full max-w-5xl">
        <div className="mb-8 text-center">
          <h2 className="text-xl font-bold text-foreground sm:text-2xl">
            How are you feeling?
          </h2>
          <p className="mt-2 text-sm text-muted-foreground">
            Select what resonates most with your current state
          </p>
        </div>

        <div className="mx-auto grid max-w-4xl grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {MOOD_OPTIONS.map((mood) => (
            <MoodCard key={mood.type} mood={mood} onSelect={onSelect} />
          ))}
        </div>
      </div>
    </div>
  )
}
