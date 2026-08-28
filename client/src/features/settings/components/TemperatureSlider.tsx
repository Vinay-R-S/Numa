"use client"

import { Thermometer } from "lucide-react"

/** Sampling temperature, 0 to 2 in 0.05 steps, mirroring the server bounds. */
export function TemperatureSlider({
  value,
  onChange,
}: {
  value: number
  onChange: (value: number) => void
}) {
  return (
    <div className="mt-3">
      <div className="mb-1.5 flex items-center justify-between">
        <label className="flex items-center gap-1 text-xs font-medium text-muted-foreground">
          <Thermometer className="h-3 w-3" />
          Temperature
        </label>
        <span className="text-xs font-mono text-foreground">{value.toFixed(2)}</span>
      </div>
      <input
        type="range"
        min="0"
        max="2"
        step="0.05"
        value={value}
        onChange={(e) => onChange(parseFloat(e.target.value))}
        className="w-full accent-primary"
      />
      <div className="flex justify-between text-[10px] text-muted-foreground">
        <span>Precise</span>
        <span>Creative</span>
      </div>
    </div>
  )
}
