"use client"

import { Pause, Play, RotateCcw } from "lucide-react"
import { Button } from "@/components/ui/button"
import { TIMER_PRESETS } from "../mentalPeace.constants"
import { formatCountdown } from "../mentalPeace.utils"
import { useMeditationTimer } from "../useMeditationTimer"

const RADIUS = 54
const CIRCUMFERENCE = 2 * Math.PI * RADIUS

export function MeditationTimer() {
  const { selectedTime, timeLeft, isRunning, progress, selectPreset, toggleRunning, reset } =
    useMeditationTimer()

  return (
    <div className="w-full max-w-[280px] rounded-2xl border border-border/40 bg-card/40 p-4 sm:p-6">
      <h3 className="mb-4 text-sm font-medium text-foreground">
        Meditation Timer
      </h3>

      <div className="relative mb-6">
        <svg className="h-auto w-full" viewBox="0 0 120 120">
          <circle cx="60" cy="60" r={RADIUS} fill="none" className="stroke-border/40" strokeWidth="4" />
          <circle
            cx="60"
            cy="60"
            r={RADIUS}
            fill="none"
            className="stroke-primary"
            strokeWidth="4"
            strokeLinecap="round"
            strokeDasharray={CIRCUMFERENCE}
            strokeDashoffset={CIRCUMFERENCE * (1 - progress / 100)}
            transform="rotate(-90 60 60)"
            style={{ transition: "stroke-dashoffset 0.5s ease" }}
          />
        </svg>

        <div className="absolute inset-0 flex items-center justify-center">
          <span className="text-2xl font-light tabular-nums text-foreground sm:text-3xl">
            {formatCountdown(timeLeft)}
          </span>
        </div>
      </div>

      <div className="mb-4 flex gap-2">
        {TIMER_PRESETS.map((preset) => (
          <button
            key={preset.seconds}
            onClick={() => selectPreset(preset.seconds)}
            className={`flex-1 rounded-lg border py-1.5 text-xs transition-colors ${
              selectedTime === preset.seconds
                ? "border-primary/40 bg-primary/10 text-primary"
                : "border-border/30 bg-card/20 text-muted-foreground"
            }`}
          >
            {preset.label}
          </button>
        ))}
      </div>

      <div className="flex gap-3">
        <Button onClick={toggleRunning} className="flex-1 gap-2">
          {isRunning ? (
            <><Pause className="h-4 w-4" /> Pause</>
          ) : (
            <><Play className="h-4 w-4" /> Start</>
          )}
        </Button>
        <Button variant="outline" size="icon" onClick={reset}>
          <RotateCcw className="h-4 w-4" />
        </Button>
      </div>
    </div>
  )
}
