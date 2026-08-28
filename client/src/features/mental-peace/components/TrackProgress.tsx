"use client"

import type { MouseEvent } from "react"
import { formatClock } from "../mentalPeace.utils"

interface TrackProgressProps {
  elapsed: number
  duration: number
  progress: number
  onSeekToRatio: (ratio: number) => void
}

export function TrackProgress({ elapsed, duration, progress, onSeekToRatio }: TrackProgressProps) {
  const handleClick = (e: MouseEvent<HTMLDivElement>) => {
    const rect = e.currentTarget.getBoundingClientRect()
    onSeekToRatio((e.clientX - rect.left) / rect.width)
  }

  return (
    <div className="space-y-1">
      <div
        className="h-1.5 w-full cursor-pointer overflow-hidden rounded-full bg-border/30"
        onClick={handleClick}
      >
        <div className="h-full rounded-full bg-primary transition-all" style={{ width: `${progress}%` }} />
      </div>
      <div className="flex justify-between text-[10px] text-muted-foreground tabular-nums">
        <span>{formatClock(elapsed)}</span>
        <span>{formatClock(duration)}</span>
      </div>
    </div>
  )
}
