"use client"

import React, { useState, useEffect, useRef } from "react"
import { Play, Pause, RotateCcw } from "lucide-react"
import { Button } from "@/components/ui/button"

const presetTimes = [
  { label: "5 min", seconds: 5 * 60 },
  { label: "10 min", seconds: 10 * 60 },
  { label: "15 min", seconds: 15 * 60 },
  { label: "20 min", seconds: 20 * 60 },
]

export function MeditationTimer() {
  const [selectedTime, setSelectedTime] = useState(presetTimes[1].seconds)
  const [timeLeft, setTimeLeft] = useState(presetTimes[1].seconds)
  const [isRunning, setIsRunning] = useState(false)
  const intervalRef = useRef<NodeJS.Timeout | null>(null)

  useEffect(() => {
    if (isRunning && timeLeft > 0) {
      intervalRef.current = setInterval(() => {
        setTimeLeft((prev) => {
          if (prev <= 1) {
            setIsRunning(false)
            if (typeof window !== "undefined") {
              const AudioContextClass = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext
              if (AudioContextClass) {
                const ctx = new AudioContextClass()
                const osc = ctx.createOscillator()
                const gain = ctx.createGain()
                osc.type = "sine"
                osc.frequency.setValueAtTime(528, ctx.currentTime)
                gain.gain.setValueAtTime(0.1, ctx.currentTime)
                gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 2)
                osc.connect(gain)
                gain.connect(ctx.destination)
                osc.start()
                osc.stop(ctx.currentTime + 2)
              }
            }
            return 0
          }
          return prev - 1
        })
      }, 1000)
    }

    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current)
    }
  }, [isRunning, timeLeft])

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${mins.toString().padStart(2, "0")}:${secs.toString().padStart(2, "0")}`
  }

  const handlePresetClick = (seconds: number) => {
    setSelectedTime(seconds)
    setTimeLeft(seconds)
    setIsRunning(false)
  }

  const handleReset = () => {
    setTimeLeft(selectedTime)
    setIsRunning(false)
  }

  const progress = ((selectedTime - timeLeft) / selectedTime) * 100
  const circumference = 2 * Math.PI * 54

  return (
    <div className="w-full max-w-[280px] rounded-2xl border border-border/40 bg-card/40 p-4 sm:p-6">
      <h3 className="mb-4 text-sm font-medium text-foreground">
        Meditation Timer
      </h3>

      {/* Timer display */}
      <div className="relative mb-6">
        <svg className="h-auto w-full" viewBox="0 0 120 120">
          <circle
            cx="60"
            cy="60"
            r="54"
            fill="none"
            className="stroke-border/40"
            strokeWidth="4"
          />
          <circle
            cx="60"
            cy="60"
            r="54"
            fill="none"
            className="stroke-primary"
            strokeWidth="4"
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={circumference * (1 - progress / 100)}
            transform="rotate(-90 60 60)"
            style={{ transition: "stroke-dashoffset 0.5s ease" }}
          />
        </svg>

        <div className="absolute inset-0 flex items-center justify-center">
          <span className="text-2xl font-light tabular-nums text-foreground sm:text-3xl">
            {formatTime(timeLeft)}
          </span>
        </div>
      </div>

      {/* Preset buttons */}
      <div className="mb-4 flex gap-2">
        {presetTimes.map((preset) => (
          <button
            key={preset.seconds}
            onClick={() => handlePresetClick(preset.seconds)}
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

      {/* Controls */}
      <div className="flex gap-3">
        <Button
          onClick={() => setIsRunning(!isRunning)}
          className="flex-1 gap-2"
        >
          {isRunning ? (
            <><Pause className="h-4 w-4" /> Pause</>
          ) : (
            <><Play className="h-4 w-4" /> Start</>
          )}
        </Button>
        <Button
          variant="outline"
          size="icon"
          onClick={handleReset}
        >
          <RotateCcw className="h-4 w-4" />
        </Button>
      </div>
    </div>
  )
}
