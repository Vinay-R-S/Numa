"use client"

import { Pause, Play, Repeat, Repeat1, SkipBack, SkipForward, Volume2, VolumeX } from "lucide-react"
import { Button } from "@/components/ui/button"
import { SEEK_STEP_SECONDS } from "../mentalPeace.constants"

interface PlayerControlsProps {
  isPlaying: boolean
  isMuted: boolean
  isLooping: boolean
  isPreparing: boolean
  onSeekBy: (delta: number) => void
  onTogglePlay: () => void
  onToggleLoop: () => void
  onToggleMute: () => void
}

export function PlayerControls({
  isPlaying,
  isMuted,
  isLooping,
  isPreparing,
  onSeekBy,
  onTogglePlay,
  onToggleLoop,
  onToggleMute,
}: PlayerControlsProps) {
  return (
    <div className="flex items-center justify-center gap-1">
      <Button
        variant="ghost"
        size="icon"
        className="h-8 w-8"
        onClick={() => onSeekBy(-SEEK_STEP_SECONDS)}
        title={`-${SEEK_STEP_SECONDS}s`}
      >
        <SkipBack className="h-3.5 w-3.5" />
      </Button>

      <Button size="icon" className="h-10 w-10 rounded-full" onClick={onTogglePlay} disabled={isPreparing}>
        {isPlaying ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}
      </Button>

      <Button
        variant="ghost"
        size="icon"
        className="h-8 w-8"
        onClick={() => onSeekBy(SEEK_STEP_SECONDS)}
        title={`+${SEEK_STEP_SECONDS}s`}
      >
        <SkipForward className="h-3.5 w-3.5" />
      </Button>

      <Button
        variant="ghost"
        size="icon"
        className={`h-8 w-8 ${isLooping ? "text-primary" : "text-muted-foreground"}`}
        onClick={onToggleLoop}
        title={isLooping ? "Loop on" : "Loop off"}
      >
        {isLooping ? <Repeat1 className="h-3.5 w-3.5" /> : <Repeat className="h-3.5 w-3.5" />}
      </Button>

      <Button variant="ghost" size="icon" className="h-8 w-8" onClick={onToggleMute}>
        {isMuted ? <VolumeX className="h-3.5 w-3.5" /> : <Volume2 className="h-3.5 w-3.5" />}
      </Button>
    </div>
  )
}
