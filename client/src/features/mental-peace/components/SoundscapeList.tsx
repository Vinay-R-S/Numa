"use client"

import { SOUNDSCAPES } from "../mentalPeace.constants"
import type { Soundscape } from "../mentalPeace.types"

interface SoundscapeListProps {
  activeId: string | null
  isPlaying: boolean
  isPreparing: boolean
  onSelect: (soundscape: Soundscape) => void
}

const EQUALIZER_BARS = [1, 2, 3]

export function SoundscapeList({ activeId, isPlaying, isPreparing, onSelect }: SoundscapeListProps) {
  return (
    <div className="space-y-1.5">
      {SOUNDSCAPES.map((soundscape) => {
        const isActive = activeId === soundscape.id

        return (
          <button
            key={soundscape.id}
            onClick={() => onSelect(soundscape)}
            disabled={isPreparing}
            className={`w-full rounded-lg border p-2.5 text-left transition-colors disabled:cursor-wait disabled:opacity-60 ${
              isActive ? "border-primary/40 bg-primary/10" : "border-border/40 bg-card/20 hover:border-primary/20"
            }`}
          >
            <div className="flex items-center justify-between gap-2">
              <div className="min-w-0">
                <p className={`text-xs font-medium ${isActive ? "text-primary" : "text-foreground"}`}>
                  {soundscape.name}
                </p>
                <p className="text-[10px] text-muted-foreground">
                  {soundscape.description}
                </p>
              </div>
              {isActive && isPlaying && (
                <div className="flex shrink-0 gap-0.5">
                  {EQUALIZER_BARS.map((bar) => (
                    <div
                      key={bar}
                      className="w-0.5 rounded-full bg-primary animate-pulse"
                      style={{ height: `${6 + bar * 2}px`, animationDelay: `${bar * 100}ms` }}
                    />
                  ))}
                </div>
              )}
            </div>
          </button>
        )
      })}
    </div>
  )
}
