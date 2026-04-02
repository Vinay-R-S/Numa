"use client"

import React, { useState, useEffect, useRef } from "react"
import { motion } from "framer-motion"
import { Play, Pause, RotateCcw } from "lucide-react"

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
            // Play completion sound
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
      if (intervalRef.current) {
        clearInterval(intervalRef.current)
      }
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

  return (
    <div
      className="w-[280px] rounded-2xl p-6"
      style={{
        background: "rgba(255, 255, 255, 0.03)",
        backdropFilter: "blur(12px)",
        border: "1px solid rgba(255, 255, 255, 0.08)",
      }}
    >
      <h3
        className="text-sm font-medium mb-4"
        style={{
          fontFamily: "'Cinzel', serif",
          color: "#a78bfa",
        }}
      >
        Meditation Timer
      </h3>

      {/* Timer display */}
      <div className="relative mb-6">
        {/* Progress ring */}
        <svg className="w-full h-auto" viewBox="0 0 120 120">
          <circle
            cx="60"
            cy="60"
            r="54"
            fill="none"
            stroke="rgba(126,200,200,0.15)"
            strokeWidth="4"
          />
          <motion.circle
            cx="60"
            cy="60"
            r="54"
            fill="none"
            stroke="url(#timerGradientCool)"
            strokeWidth="4"
            strokeLinecap="round"
            strokeDasharray={339.292}
            strokeDashoffset={339.292 * (1 - progress / 100)}
            transform="rotate(-90 60 60)"
            initial={false}
            animate={{ strokeDashoffset: 339.292 * (1 - progress / 100) }}
            transition={{ duration: 0.5 }}
          />
          <defs>
            <linearGradient id="timerGradientCool" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor="#7ec8c8" />
              <stop offset="100%" stopColor="#a78bfa" />
            </linearGradient>
          </defs>
        </svg>

        {/* Time display */}
        <div className="absolute inset-0 flex items-center justify-center">
          <span
            className="text-3xl font-light tabular-nums"
            style={{
              fontFamily: "'Cinzel', serif",
              color: "#f0f0f0",
            }}
          >
            {formatTime(timeLeft)}
          </span>
        </div>
      </div>

      {/* Preset buttons */}
      <div className="flex gap-2 mb-4">
        {presetTimes.map((preset) => (
          <button
            key={preset.seconds}
            onClick={() => handlePresetClick(preset.seconds)}
            className="flex-1 py-1.5 text-xs rounded-lg transition-all duration-300"
            style={{
              fontFamily: "'Crimson Pro', serif",
              background: selectedTime === preset.seconds ? "rgba(126,200,200,0.2)" : "rgba(255, 255, 255, 0.02)",
              color: selectedTime === preset.seconds ? "#7ec8c8" : "#9ca3af",
              border: selectedTime === preset.seconds ? "1px solid rgba(126,200,200,0.4)" : "1px solid rgba(255, 255, 255, 0.05)",
            }}
          >
            {preset.label}
          </button>
        ))}
      </div>

      {/* Controls */}
      <div className="flex gap-3">
        <motion.button
          onClick={() => setIsRunning(!isRunning)}
          whileHover={{ scale: 1.02, boxShadow: "0 0 20px rgba(126,200,200,0.3)" }}
          whileTap={{ scale: 0.98 }}
          className="flex-1 py-3 rounded-lg text-white font-medium flex items-center justify-center gap-2"
          style={{
            fontFamily: "'Cinzel', serif",
            letterSpacing: "0.1em",
            fontSize: "0.875rem",
            background: "linear-gradient(135deg, #7ec8c8 0%, #6366f1 100%)",
          }}
        >
          {isRunning ? (
            <>
              <Pause className="w-4 h-4" /> PAUSE
            </>
          ) : (
            <>
              <Play className="w-4 h-4" /> START
            </>
          )}
        </motion.button>
        <motion.button
          onClick={handleReset}
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          className="p-3 rounded-lg transition-colors duration-300"
          style={{
            background: "rgba(255, 255, 255, 0.02)",
            border: "1px solid rgba(255, 255, 255, 0.08)",
            color: "#9ca3af",
          }}
        >
          <RotateCcw className="w-4 h-4" />
        </motion.button>
      </div>
    </div>
  )
}
