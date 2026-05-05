"use client"

import React from "react"
import { Waves, Sun, Zap, Circle, Moon } from "lucide-react"
import { MoodType, moodConfig } from "../yogaData"

interface MoodSelectorProps {
  onSelect: (mood: MoodType) => void
}

const moods: { type: MoodType; description: string; icon: React.ReactNode }[] = [
  { type: "overwhelmed", description: "Mind racing, too much happening", icon: <Waves className="h-6 w-6" /> },
  { type: "low", description: "Lacking energy or motivation", icon: <Sun className="h-6 w-6" /> },
  { type: "restless", description: "Can't settle, fidgety energy", icon: <Zap className="h-6 w-6" /> },
  { type: "numb", description: "Feeling disconnected or flat", icon: <Circle className="h-6 w-6" /> },
  { type: "exhausted", description: "Deeply tired, need restoration", icon: <Moon className="h-6 w-6" /> },
]

export function MoodSelector({ onSelect }: MoodSelectorProps) {
  return (
    <div className="min-h-screen flex items-center justify-center bg-background px-4 py-12">
      <div className="w-full max-w-4xl">
        <div className="mb-8 text-center sm:mb-12">
          <h2 className="text-xl font-bold text-foreground sm:text-2xl">
            How are you feeling?
          </h2>
          <p className="mt-2 text-sm text-muted-foreground">
            Select what resonates most with your current state
          </p>
        </div>

        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 sm:gap-4 lg:grid-cols-5">
          {moods.map((mood) => {
            const config = moodConfig[mood.type]
            return (
              <button
                key={mood.type}
                onClick={() => onSelect(mood.type)}
                className="rounded-2xl border border-border/40 bg-card/40 px-3 py-5 text-center transition-colors hover:border-primary/30 hover:bg-card/60 sm:px-4 sm:py-8"
              >
                <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-xl border border-border/40 bg-background text-muted-foreground">
                  {mood.icon}
                </div>
                <h3 className="text-sm font-medium text-foreground">
                  {config.label}
                </h3>
                <p className="mt-1 text-xs text-muted-foreground">
                  {mood.description}
                </p>
              </button>
            )
          })}
        </div>
      </div>
    </div>
  )
}
