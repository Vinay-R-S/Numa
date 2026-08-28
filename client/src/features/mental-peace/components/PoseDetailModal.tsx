"use client"

import { X } from "lucide-react"
import { DifficultyDots } from "./DifficultyDots"
import { PoseImage } from "./PoseImage"
import type { PoseWithMoodReason } from "../mentalPeace.types"

interface PoseDetailModalProps {
  pose: PoseWithMoodReason
  onClose: () => void
}

export function PoseDetailModal({ pose, onClose }: PoseDetailModalProps) {
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-2 sm:p-4"
      onClick={onClose}
    >
      <div
        className="max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-2xl border border-border/40 bg-background sm:max-h-[85vh]"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="relative h-40 overflow-hidden rounded-t-2xl sm:h-56">
          <PoseImage
            pose={pose}
            className="h-full w-full object-contain"
            style={{ backgroundColor: "rgba(0,0,0,0.3)" }}
            fallbackClassName="flex h-full w-full items-center justify-center bg-card/40"
            fallbackTextClassName="text-center text-xl font-medium text-primary"
          />
          <div className="absolute inset-0 bg-linear-to-t from-background via-transparent to-transparent" />
          <button
            onClick={onClose}
            className="absolute right-4 top-4 rounded-full bg-black/50 p-2 text-foreground transition-colors hover:bg-black/70"
          >
            <X className="h-5 w-5" />
          </button>
          <div className="absolute bottom-4 left-6 right-6">
            <h2 className="text-xl font-bold text-foreground sm:text-2xl">
              {pose.englishName}
            </h2>
            <p className="text-sm italic text-primary">
              {pose.sanskritName}
            </p>
            <p className="text-xs text-muted-foreground">({pose.pronunciation})</p>
          </div>
        </div>

        <div className="p-4 sm:p-6">
          <div className="mb-6 rounded-2xl border border-border/40 bg-card/40 p-4">
            <p className="text-sm italic text-muted-foreground">
              &ldquo;{pose.moodReason}&rdquo;
            </p>
          </div>

          <div className="mb-6 flex items-center gap-6">
            <div>
              <p className="mb-1 text-xs text-muted-foreground">Difficulty</p>
              <DifficultyDots level={pose.difficulty} />
            </div>
            <div>
              <p className="mb-1 text-xs text-muted-foreground">Hold Duration</p>
              <p className="text-sm text-foreground">{pose.duration}</p>
            </div>
          </div>

          <div className="my-6 h-px w-full bg-border/40" />

          <div className="mb-6">
            <h3 className="mb-3 text-sm font-medium text-primary">
              Instructions
            </h3>
            <ol className="space-y-2">
              {pose.instructions.map((step, i) => (
                <li key={step} className="flex gap-3 text-sm text-foreground/80">
                  <span className="shrink-0 font-medium text-muted-foreground">
                    {i + 1}.
                  </span>
                  <span>{step}</span>
                </li>
              ))}
            </ol>
          </div>

          <div className="my-6 h-px w-full bg-border/40" />

          <div>
            <h3 className="mb-3 text-sm font-medium text-primary">
              Benefits
            </h3>
            <p className="text-sm leading-relaxed text-foreground/80">
              {pose.benefits}
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
