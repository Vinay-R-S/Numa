"use client"

import React from "react"
import { Angry, Annoyed, Bed, Frown, Meh, PersonStanding } from "lucide-react"
import { MoodType, moodConfig } from "../yogaData"

interface MoodSelectorProps {
  onSelect: (mood: MoodType | "meditation") => void
}

const yogaMoods: { type: MoodType; description: string; icon: React.ReactNode }[] = [
  { type: "overwhelmed", description: "Mind racing, too much happening", icon: <Angry className="h-7 w-7" /> },
  { type: "low", description: "Lacking energy or motivation", icon: <Frown className="h-7 w-7" /> },
  { type: "restless", description: "Can't settle, fidgety energy", icon: <Annoyed className="h-7 w-7" /> },
  { type: "numb", description: "Feeling disconnected or flat", icon: <Meh className="h-7 w-7" /> },
  { type: "exhausted", description: "Deeply tired, need restoration", icon: <Bed className="h-7 w-7" /> },
]

const moods: { type: MoodType | "meditation"; label: string; description: string; icon: React.ReactNode }[] = [
  ...yogaMoods.map((mood) => ({
    ...mood,
    label: moodConfig[mood.type].label,
  })),
  {
    type: "meditation",
    label: "Meditation",
    description: "Music, timer, and seated posture",
    icon: <PersonStanding className="h-7 w-7" />,
  },
]

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
          {moods.map((mood) => {
            return (
              <button
                key={mood.type}
                onClick={() => onSelect(mood.type)}
                className="flex h-52 flex-col rounded-2xl border border-border/40 bg-card/40 px-5 py-6 text-center transition-colors hover:border-primary/30 hover:bg-card/60"
              >
                <div className="mx-auto flex h-14 w-14 shrink-0 items-center justify-center rounded-xl border border-border/40 bg-background text-muted-foreground">
                  {mood.icon}
                </div>
                <div className="mt-5 flex flex-1 flex-col justify-start">
                  <h3 className="text-base font-semibold leading-tight text-foreground">
                    {mood.label}
                  </h3>
                  <p className="mx-auto mt-2 max-w-[12rem] text-sm leading-snug text-muted-foreground">
                    {mood.description}
                  </p>
                </div>
              </button>
            )
          })}
        </div>
      </div>
    </div>
  )
}
