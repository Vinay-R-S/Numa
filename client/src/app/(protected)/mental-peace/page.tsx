"use client"

import React, { useState } from "react"
import { AnimatePresence, motion } from "framer-motion"
import { MoodType } from "./yogaData"
import { EntryScreen } from "./components/EntryScreen"
import { MoodSelector } from "./components/MoodSelector"
import { PreparingSession } from "./components/PreparingSession"
import { Dashboard } from "./components/Dashboard"
import { GuidedSession } from "./components/GuidedSession"
import { ReflectionCard } from "./components/ReflectionCard"

// Stage enum for clarity
const STAGES = {
  ENTRY: 0,
  MOOD_SELECT: 1,
  PREPARING: 2,
  DASHBOARD: 3,
  GUIDED_SESSION: 4,
  REFLECTION: 5,
} as const

// Animation variants for page transitions
const pageVariants = {
  initial: { opacity: 0, y: 20 },
  animate: { opacity: 1, y: 0 },
  exit: { opacity: 0, y: -20 },
}

const pageTransition = {
  duration: 0.4,
  ease: [0.25, 0.1, 0.25, 1] as const,
}

export default function MentalPeacePage() {
  const [stage, setStage] = useState<number>(STAGES.ENTRY)
  const [selectedMood, setSelectedMood] = useState<MoodType | null>(null)

  const handleMoodSelect = (mood: MoodType) => {
    setSelectedMood(mood)
    setStage(STAGES.PREPARING)
  }

  const handleReset = () => {
    setSelectedMood(null)
    setStage(STAGES.ENTRY)
  }

  const renderStage = () => {
    switch (stage) {
      case STAGES.ENTRY:
        return (
          <motion.div
            key="entry"
            variants={pageVariants}
            initial="initial"
            animate="animate"
            exit="exit"
            transition={pageTransition}
            className="min-h-screen"
          >
            <EntryScreen onBegin={() => setStage(STAGES.MOOD_SELECT)} />
          </motion.div>
        )

      case STAGES.MOOD_SELECT:
        return (
          <motion.div
            key="mood"
            variants={pageVariants}
            initial="initial"
            animate="animate"
            exit="exit"
            transition={pageTransition}
            className="min-h-screen"
          >
            <MoodSelector onSelect={handleMoodSelect} />
          </motion.div>
        )

      case STAGES.PREPARING:
        return (
          <motion.div
            key="preparing"
            variants={pageVariants}
            initial="initial"
            animate="animate"
            exit="exit"
            transition={pageTransition}
            className="min-h-screen"
          >
            <PreparingSession
              mood={selectedMood!}
              onComplete={() => setStage(STAGES.DASHBOARD)}
            />
          </motion.div>
        )

      case STAGES.DASHBOARD:
        return (
          <motion.div
            key="dashboard"
            variants={pageVariants}
            initial="initial"
            animate="animate"
            exit="exit"
            transition={pageTransition}
            className="min-h-screen"
          >
            <Dashboard
              mood={selectedMood!}
              onBeginSession={() => setStage(STAGES.GUIDED_SESSION)}
            />
          </motion.div>
        )

      case STAGES.GUIDED_SESSION:
        return (
          <motion.div
            key="guided"
            variants={pageVariants}
            initial="initial"
            animate="animate"
            exit="exit"
            transition={pageTransition}
            className="fixed inset-0 z-50"
          >
            <GuidedSession
              mood={selectedMood!}
              onEnd={() => setStage(STAGES.REFLECTION)}
            />
          </motion.div>
        )

      case STAGES.REFLECTION:
        return (
          <motion.div
            key="reflection"
            variants={pageVariants}
            initial="initial"
            animate="animate"
            exit="exit"
            transition={pageTransition}
            className="min-h-screen"
          >
            <ReflectionCard onComplete={handleReset} />
          </motion.div>
        )

      default:
        return null
    }
  }

  return (
    <div className="min-h-screen bg-[#0d0f14] text-[#f0f0f0] overflow-x-hidden">
      {/* Subtle mandala watermark with cool teal colors */}
      <div className="fixed inset-0 pointer-events-none overflow-hidden">
        <svg
          className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[800px] opacity-[0.04]"
          viewBox="0 0 400 400"
        >
          {/* Concentric circles */}
          {[60, 90, 120, 150, 180].map((r, i) => (
            <circle
              key={i}
              cx="200"
              cy="200"
              r={r}
              fill="none"
              stroke="#7ec8c8"
              strokeWidth="0.5"
            />
          ))}
          {/* Geometric petals */}
          {[...Array(12)].map((_, i) => {
            const angle = (i * 30 * Math.PI) / 180
            const x1 = 200 + Math.cos(angle) * 60
            const y1 = 200 + Math.sin(angle) * 60
            const x2 = 200 + Math.cos(angle) * 180
            const y2 = 200 + Math.sin(angle) * 180
            return (
              <line
                key={i}
                x1={x1}
                y1={y1}
                x2={x2}
                y2={y2}
                stroke="#a78bfa"
                strokeWidth="0.5"
              />
            )
          })}
          {/* Inner lotus petals */}
          {[...Array(8)].map((_, i) => {
            const angle = (i * 45 * Math.PI) / 180
            const cx = 200 + Math.cos(angle) * 45
            const cy = 200 + Math.sin(angle) * 45
            return (
              <ellipse
                key={i}
                cx={cx}
                cy={cy}
                rx="15"
                ry="8"
                fill="none"
                stroke="#7ec8c8"
                strokeWidth="0.5"
                transform={`rotate(${i * 45 + 90} ${cx} ${cy})`}
              />
            )
          })}
        </svg>
      </div>

      <AnimatePresence mode="wait">
        {renderStage()}
      </AnimatePresence>
    </div>
  )
}
