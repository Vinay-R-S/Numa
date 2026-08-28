"use client"

import { Volume2, VolumeX } from "lucide-react"

interface VolumeSliderProps {
  volume: number
  isMuted: boolean
  onChange: (value: number) => void
}

export function VolumeSlider({ volume, isMuted, onChange }: VolumeSliderProps) {
  return (
    <div className="flex items-center gap-2">
      <VolumeX className="h-3 w-3 shrink-0 text-muted-foreground" />
      <input
        type="range"
        min="0"
        max="1"
        step="0.01"
        value={isMuted ? 0 : volume}
        onChange={(e) => onChange(parseFloat(e.target.value))}
        className="h-1 w-full accent-primary"
      />
      <Volume2 className="h-3 w-3 shrink-0 text-muted-foreground" />
    </div>
  )
}
