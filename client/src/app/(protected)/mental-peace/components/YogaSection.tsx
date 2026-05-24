"use client"

import React, { useState } from "react"
import { X } from "lucide-react"
import { Button } from "@/components/ui/button"
import { moodConfig, MoodType, getPosesForMood, PoseWithMoodReason } from "../yogaData"

interface YogaSectionProps {
  mood: MoodType
  onBeginSession: () => void
}

function DifficultyDots({ level }: { level: number }) {
  return (
    <div className="flex gap-1">
      {[...Array(5)].map((_, i) => (
        <span
          key={i}
          className={`h-1.5 w-1.5 rounded-full ${
            i < level ? "bg-primary" : "bg-border/40"
          }`}
        />
      ))}
    </div>
  )
}

function PoseCardImage({ pose }: { pose: PoseWithMoodReason }) {
  const [imageError, setImageError] = useState(false)

  if (imageError) {
    return (
      <div className="flex h-[160px] w-full items-center justify-center border-b border-border/40 bg-card/40 p-4">
        <span className="text-center text-sm font-medium text-primary">
          {pose.englishName}
        </span>
      </div>
    )
  }

  return (
    // eslint-disable-next-line @next/next/no-img-element
    <img
      src={pose.imageUrl}
      alt={pose.englishName}
      className="h-[160px] w-full object-contain"
      style={{ backgroundColor: "rgba(0,0,0,0.2)" }}
      onError={() => setImageError(true)}
    />
  )
}

function PoseCard({ pose, onViewDetails }: { pose: PoseWithMoodReason; onViewDetails: () => void }) {
  return (
    <div
      className="w-[160px] shrink-0 cursor-pointer overflow-hidden rounded-2xl border border-border/40 bg-card/40 transition-colors hover:border-primary/30 sm:w-[200px]"
      onClick={onViewDetails}
    >
      <div className="overflow-hidden rounded-t-2xl">
        <PoseCardImage pose={pose} />
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

function ModalPoseImage({ pose }: { pose: PoseWithMoodReason }) {
  const [imageError, setImageError] = useState(false)

  if (imageError) {
    return (
      <div className="flex h-full w-full items-center justify-center bg-card/40">
        <span className="text-center text-xl font-medium text-primary">
          {pose.englishName}
        </span>
      </div>
    )
  }

  return (
    // eslint-disable-next-line @next/next/no-img-element
    <img
      src={pose.imageUrl}
      alt={pose.englishName}
      className="h-full w-full object-contain"
      style={{ backgroundColor: "rgba(0,0,0,0.3)" }}
      onError={() => setImageError(true)}
    />
  )
}

function PoseDetailModal({ pose, onClose }: { pose: PoseWithMoodReason; onClose: () => void }) {
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-2 sm:p-4"
      onClick={onClose}
    >
      <div
        className="max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-2xl border border-border/40 bg-background sm:max-h-[85vh]"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="relative h-40 overflow-hidden rounded-t-2xl sm:h-56">
          <ModalPoseImage pose={pose} />
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

        {/* Content */}
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
                <li key={i} className="flex gap-3 text-sm text-foreground/80">
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

export function YogaSection({ mood, onBeginSession }: YogaSectionProps) {
  const [selectedPose, setSelectedPose] = useState<PoseWithMoodReason | null>(null)
  const config = moodConfig[mood]
  const poses = getPosesForMood(mood)

  return (
    <div className="min-w-0 flex-1">
      <div className="mb-6">
        <h2 className="text-xl font-bold text-foreground sm:text-2xl">
          {config.sequenceName}
        </h2>
        <p className="mt-1 text-sm text-muted-foreground">
          {config.flowSubtitle}
        </p>
      </div>

      {/* Scrollable pose cards */}
      <div className="relative mb-8">
        <div className="flex gap-4 overflow-x-auto pb-4">
          {poses.map((pose) => (
            <PoseCard
              key={pose.id}
              pose={pose}
              onViewDetails={() => setSelectedPose(pose)}
            />
          ))}
        </div>
        <div className="pointer-events-none absolute bottom-4 right-0 top-0 w-16 bg-linear-to-l from-background to-transparent" />
      </div>

      <Button onClick={onBeginSession} size="lg">
        Begin Session
      </Button>

      {selectedPose && (
        <PoseDetailModal
          pose={selectedPose}
          onClose={() => setSelectedPose(null)}
        />
      )}
    </div>
  )
}
