"use client"

import { useState } from "react"
import type { CSSProperties } from "react"
import type { YogaPose } from "../mentalPeace.types"

interface PoseFallbackProps {
  pose: YogaPose
  className: string
  textClassName: string
}

/** Shown when a remote pose image fails to load; three screens rendered this. */
export function PoseFallback({ pose, className, textClassName }: PoseFallbackProps) {
  return (
    <div className={className}>
      <span className={textClassName}>{pose.englishName}</span>
    </div>
  )
}

interface PoseImageProps {
  pose: YogaPose
  className: string
  style?: CSSProperties
  fallbackClassName: string
  fallbackTextClassName: string
}

export function PoseImage({
  pose,
  className,
  style,
  fallbackClassName,
  fallbackTextClassName,
}: PoseImageProps) {
  const [imageError, setImageError] = useState(false)

  if (imageError) {
    return (
      <PoseFallback pose={pose} className={fallbackClassName} textClassName={fallbackTextClassName} />
    )
  }

  return (
    // eslint-disable-next-line @next/next/no-img-element
    <img
      src={pose.imageUrl}
      alt={pose.englishName}
      className={className}
      style={style}
      onError={() => setImageError(true)}
    />
  )
}
