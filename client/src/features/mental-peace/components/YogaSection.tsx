"use client"

import { useMemo, useState } from "react"
import { Button } from "@/components/ui/button"
import { moodConfig } from "../data"
import { getPosesForMood } from "../mentalPeace.utils"
import { PoseCard } from "./PoseCard"
import { PoseDetailModal } from "./PoseDetailModal"
import type { MoodType, PoseWithMoodReason } from "../mentalPeace.types"

interface YogaSectionProps {
  mood: MoodType
  onBeginSession: () => void
}

export function YogaSection({ mood, onBeginSession }: YogaSectionProps) {
  const [selectedPose, setSelectedPose] = useState<PoseWithMoodReason | null>(null)
  const config = moodConfig[mood]
  const poses = useMemo(() => getPosesForMood(mood), [mood])

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

      <div className="relative mb-8">
        <div className="flex gap-4 overflow-x-auto pb-4">
          {poses.map((pose) => (
            <PoseCard key={pose.id} pose={pose} onViewDetails={() => setSelectedPose(pose)} />
          ))}
        </div>
        <div className="pointer-events-none absolute bottom-4 right-0 top-0 w-16 bg-linear-to-l from-background to-transparent" />
      </div>

      <Button onClick={onBeginSession} size="lg">
        Begin Session
      </Button>

      {selectedPose && (
        <PoseDetailModal pose={selectedPose} onClose={() => setSelectedPose(null)} />
      )}
    </div>
  )
}
