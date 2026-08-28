"use client"

import { DifficultyDots } from "./DifficultyDots"
import { PoseImage } from "./PoseImage"
import type { PoseWithMoodReason } from "../mentalPeace.types"

interface PoseCardProps {
  pose: PoseWithMoodReason
  onViewDetails: () => void
}

export function PoseCard({ pose, onViewDetails }: PoseCardProps) {
  return (
    <div
      className="w-[160px] shrink-0 cursor-pointer overflow-hidden rounded-2xl border border-border/40 bg-card/40 transition-colors hover:border-primary/30 sm:w-[200px]"
      onClick={onViewDetails}
    >
      <div className="overflow-hidden rounded-t-2xl">
        <PoseImage
          pose={pose}
          className="h-[160px] w-full object-contain"
          style={{ backgroundColor: "rgba(0,0,0,0.2)" }}
          fallbackClassName="flex h-[160px] w-full items-center justify-center border-b border-border/40 bg-card/40 p-4"
          fallbackTextClassName="text-center text-sm font-medium text-primary"
        />
      </div>

      <div className="p-3">
        <h4 className="text-sm font-medium text-foreground">
          {pose.englishName}
        </h4>
        <p className="text-xs italic text-primary">
          {pose.sanskritName}
        </p>
        <p className="mt-1 line-clamp-2 text-[10px] italic text-muted-foreground">
          &ldquo;{pose.moodReason}&rdquo;
        </p>
        <div className="mt-2 flex items-center justify-between">
          <DifficultyDots level={pose.difficulty} />
          <span className="text-xs text-muted-foreground">{pose.duration}</span>
        </div>
      </div>
    </div>
  )
}
