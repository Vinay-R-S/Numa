"use client"

import React, { useState, useEffect, useRef, useCallback } from "react"
import { motion, AnimatePresence } from "framer-motion"

type BreathPhase = "inhale" | "hold" | "exhale"

const phaseConfig = {
  inhale: { duration: 4000, label: "Inhale...", color: "#7ec8c8", frequency: 396 },
  hold: { duration: 2000, label: "Hold...", color: "#a78bfa", frequency: 528 },
  exhale: { duration: 4000, label: "Exhale...", color: "#6366f1", frequency: 417 },
}

const phaseSequence: BreathPhase[] = ["inhale", "hold", "exhale"]

// Play a gentle bell sound at phase transitions
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

    // Clean up after sound finishes
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

    // Play bell sound at phase transition
    playBreathBell(phaseConfig[nextPhase].frequency)
  }, [phaseIndex])

  useEffect(() => {
    if (!isActive) return

    // Play initial bell
    playBreathBell(phaseConfig[currentPhase].frequency)

    // Set up timer for phase transitions
    timerRef.current = setTimeout(() => {
      advancePhase()
    }, phaseConfig[currentPhase].duration)

    return () => {
      if (timerRef.current) {
        clearTimeout(timerRef.current)
      }
    }
  }, [currentPhase, isActive, advancePhase])

  const config = phaseConfig[currentPhase]

  // Calculate orb size based on phase
  const orbSize = currentPhase === "inhale" || currentPhase === "hold" ? 120 : 80

  return (
    <div className="flex flex-col items-center">
      {/* Pulsing orb */}
      <div className="relative mb-4">
        {/* Glow effect */}
        <motion.div
          className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 rounded-full blur-xl"
          animate={{
            width: orbSize + 40,
            height: orbSize + 40,
            backgroundColor: config.color,
            opacity: 0.3,
          }}
          transition={{
            duration: currentPhase === "inhale" ? 4 : currentPhase === "exhale" ? 4 : 0.3,
            ease: "easeInOut",
          }}
        />

        {/* Main orb */}
        <motion.div
          className="relative rounded-full"
          style={{
            boxShadow: `0 0 30px ${config.color}40`,
          }}
          animate={{
            width: orbSize,
            height: orbSize,
            backgroundColor: config.color,
          }}
          transition={{
            duration: currentPhase === "inhale" ? 4 : currentPhase === "exhale" ? 4 : 0.3,
            ease: "easeInOut",
          }}
        />
      </div>

      {/* Phase text */}
      <AnimatePresence mode="wait">
        <motion.p
          key={currentPhase}
          initial={{ opacity: 0, y: 5 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -5 }}
          transition={{ duration: 0.3 }}
          className="text-lg"
          style={{
            fontFamily: "'Crimson Pro', serif",
            fontStyle: "italic",
            color: config.color,
          }}
        >
          {config.label}
        </motion.p>
      </AnimatePresence>
    </div>
  )
}
