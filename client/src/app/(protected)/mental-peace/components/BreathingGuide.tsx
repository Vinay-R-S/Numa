"use client"

import React, { useState, useEffect, useRef, useCallback } from "react"

type BreathPhase = "inhale" | "hold" | "exhale"

const phaseConfig = {
  inhale: { duration: 4000, label: "Inhale...", frequency: 396 },
  hold: { duration: 2000, label: "Hold...", frequency: 528 },
  exhale: { duration: 4000, label: "Exhale...", frequency: 417 },
}

const phaseSequence: BreathPhase[] = ["inhale", "hold", "exhale"]

function playBreathBell(frequency: number) {
  if (typeof window === "undefined") return

  const AudioContextClass = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext
  if (!AudioContextClass) return

  try {
    const ctx = new AudioContextClass()
    const osc = ctx.createOscillator()
    const gain = ctx.createGain()

    osc.connect(gain)
    gain.connect(ctx.destination)

    osc.frequency.value = frequency
    osc.type = "sine"

    gain.gain.setValueAtTime(0, ctx.currentTime)
    gain.gain.linearRampToValueAtTime(0.08, ctx.currentTime + 0.1)
    gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 1.5)

    osc.start(ctx.currentTime)
    osc.stop(ctx.currentTime + 1.5)

    setTimeout(() => ctx.close(), 2000)
  } catch {}
}

interface BreathingGuideProps {
  isActive?: boolean
}

export function BreathingGuide({ isActive = true }: BreathingGuideProps) {
  const [currentPhase, setCurrentPhase] = useState<BreathPhase>("inhale")
  const [phaseIndex, setPhaseIndex] = useState(0)
  const timerRef = useRef<NodeJS.Timeout | null>(null)

  const advancePhase = useCallback(() => {
    const nextIndex = (phaseIndex + 1) % phaseSequence.length
    const nextPhase = phaseSequence[nextIndex]

    setPhaseIndex(nextIndex)
    setCurrentPhase(nextPhase)
    playBreathBell(phaseConfig[nextPhase].frequency)
  }, [phaseIndex])

  useEffect(() => {
    if (!isActive) return

    playBreathBell(phaseConfig[currentPhase].frequency)

    timerRef.current = setTimeout(() => {
      advancePhase()
    }, phaseConfig[currentPhase].duration)

    return () => {
      if (timerRef.current) clearTimeout(timerRef.current)
    }
  }, [currentPhase, isActive, advancePhase])

  const config = phaseConfig[currentPhase]

  const orbClass =
    currentPhase === "inhale"
      ? "h-20 w-20 sm:h-28 sm:w-28"
      : currentPhase === "hold"
        ? "h-20 w-20 sm:h-28 sm:w-28"
        : "h-14 w-14 sm:h-20 sm:w-20"

  return (
    <div className="flex flex-col items-center">
      <style jsx>{`
        @keyframes breathe-inhale {
          0% { transform: scale(0.7); opacity: 0.5; }
          100% { transform: scale(1); opacity: 0.8; }
        }
        @keyframes breathe-hold {
          0%, 100% { transform: scale(1); opacity: 0.8; }
        }
        @keyframes breathe-exhale {
          0% { transform: scale(1); opacity: 0.8; }
          100% { transform: scale(0.7); opacity: 0.5; }
        }
        .breathe-inhale {
          animation: breathe-inhale 4s ease-in-out forwards;
        }
        .breathe-hold {
          animation: breathe-hold 2s ease-in-out forwards;
        }
        .breathe-exhale {
          animation: breathe-exhale 4s ease-in-out forwards;
        }
      `}</style>

      <div className="relative mb-4 flex items-center justify-center" style={{ width: 120, height: 120 }}>
        <div
          key={`${currentPhase}-${phaseIndex}`}
          className={`rounded-full bg-primary ${
            currentPhase === "inhale"
              ? "breathe-inhale"
              : currentPhase === "hold"
                ? "breathe-hold"
                : "breathe-exhale"
          }`}
          style={{ width: 80, height: 80 }}
        />
      </div>

      <p className={`text-sm sm:text-base text-primary italic ${orbClass ? "" : ""}`}>
        {config.label}
      </p>
    </div>
  )
}
