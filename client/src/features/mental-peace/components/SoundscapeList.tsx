"use client"

import { SOUNDSCAPE_PLACEHOLDER_COUNT } from "../mentalPeace.constants"
import type { Soundscape } from "../mentalPeace.types"

interface SoundscapeListProps {
  soundscapes: Soundscape[]
  activeId: string | null
  isPlaying: boolean
  isPreparing: boolean
  onSelect: (soundscape: Soundscape) => void
  onRetry: () => void
}

const EQUALIZER_BARS = [1, 2, 3]
const PLACEHOLDER_ROWS = Array.from({ length: SOUNDSCAPE_PLACEHOLDER_COUNT }, (_, index) => index)

/** Same geometry as a real row, so the list does not resize when it arrives. */
function SoundscapePlaceholder() {
  return (
    <div className="w-full rounded-lg border border-border/40 bg-card/20 p-2.5">
      <div className="space-y-1.5">
        <div className="h-3 w-2/5 animate-pulse rounded bg-muted-foreground/20" />
        <div className="h-2 w-3/5 animate-pulse rounded bg-muted-foreground/10" />
      </div>
    </div>
  )
}

export function SoundscapeList({
  soundscapes,
  activeId,
  isPlaying,
  isPreparing,
  onSelect,
  onRetry,
}: SoundscapeListProps) {
  // The catalog comes from the audio-library call (NUMA-124). Skeletons belong
  // to the in-flight request only: a settled request with no tracks is a
  // failure, and pulsing at the user forever would hide that.
  if (isPreparing) {
    return (
      <div className="space-y-1.5">
        {PLACEHOLDER_ROWS.map((row) => (
          <SoundscapePlaceholder key={row} />
        ))}
      </div>
    )
  }

  if (soundscapes.length === 0) {
    return (
      <div className="rounded-lg border border-border/40 bg-card/20 p-2.5 text-center">
        <p className="text-[10px] text-muted-foreground">No soundscapes available</p>
        <button
          onClick={onRetry}
          className="mt-1.5 text-[10px] font-medium text-primary underline-offset-2 hover:underline"
        >
          Try again
        </button>
      </div>
    )
  }

  return (
    <div className="space-y-1.5">
      {soundscapes.map((soundscape) => {
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
