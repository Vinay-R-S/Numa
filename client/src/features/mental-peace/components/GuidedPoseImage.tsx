"use client"

import Image from "next/image"
import { useState } from "react"
import { PoseFallback } from "./PoseImage"
import type { YogaPose } from "../mentalPeace.types"

/**
 * Full-bleed session image. Uses next/image (not the plain `img` the cards use)
 * because it is the one pose image rendered at full size.
 */
export function GuidedPoseImage({ pose }: { pose: YogaPose }) {
  const [imageError, setImageError] = useState(false)

  if (imageError) {
    return (
      <PoseFallback
        pose={pose}
        className="flex h-full w-full items-center justify-center rounded-2xl border border-border/40 bg-card/40 p-8"
        textClassName="text-center text-xl font-medium text-primary"
      />
    )
  }

  return (
    <Image
      src={pose.imageUrl}
      alt={pose.englishName}
      width={900}
      height={520}
      unoptimized
      className="h-full w-full rounded-2xl object-contain"
      style={{ backgroundColor: "rgba(0,0,0,0.2)" }}
      onError={() => setImageError(true)}
    />
  )
}
