"use client"

import type { MoodChoice, MoodOption } from "../mentalPeace.types"

interface MoodCardProps {
  mood: MoodOption
  onSelect: (mood: MoodChoice) => void
}

export function MoodCard({ mood, onSelect }: MoodCardProps) {
  const { icon: Icon } = mood

  return (
    <button
      onClick={() => onSelect(mood.type)}
      className="flex h-52 flex-col rounded-2xl border border-border/40 bg-card/40 px-5 py-6 text-center transition-colors hover:border-primary/30 hover:bg-card/60"
    >
      <div className="mx-auto flex h-14 w-14 shrink-0 items-center justify-center rounded-xl border border-border/40 bg-background text-muted-foreground">
        <Icon className="h-7 w-7" />
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
}
