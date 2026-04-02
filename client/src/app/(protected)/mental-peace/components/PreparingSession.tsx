"use client"

import React, { useEffect, useState } from "react"
import { motion } from "framer-motion"
import { MoodType, moodConfig } from "../yogaData"

interface PreparingSessionProps {
  mood: MoodType
  onComplete: () => void
}

const preparingMessages = [
  "Preparing your space...",
  "Selecting poses for your mood...",
  "Creating your flow...",
  "Almost ready...",
]

export function PreparingSession({ mood, onComplete }: PreparingSessionProps) {
  const [messageIndex, setMessageIndex] = useState(0)
  const [progress, setProgress] = useState(0)
  const config = moodConfig[mood]

  useEffect(() => {
    // Progress animation
    const progressInterval = setInterval(() => {
      setProgress((prev) => {
        if (prev >= 100) {
          clearInterval(progressInterval)
          return 100
        }
        return prev + 2
      })
    }, 50)

    // Message rotation
    const messageInterval = setInterval(() => {
      setMessageIndex((prev) => (prev + 1) % preparingMessages.length)
    }, 700)

    // Complete after animation
    const completeTimeout = setTimeout(() => {
      onComplete()
    }, 2800)

    return () => {
      clearInterval(progressInterval)
      clearInterval(messageInterval)
      clearTimeout(completeTimeout)
    }
  }, [onComplete])

  return (
    <div className="min-h-screen bg-[#0d0f14] flex items-center justify-center p-6">
      <div
        className="text-center max-w-md p-8 rounded-2xl"
        style={{
          background: "rgba(255, 255, 255, 0.03)",
          backdropFilter: "blur(12px)",
          border: "1px solid rgba(255, 255, 255, 0.08)",
        }}
      >
        {/* Animated lotus */}
        <motion.div
          className="mb-8"
          animate={{ scale: [1, 1.1, 1], rotate: [0, 5, -5, 0] }}
          transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
        >
          <svg
            viewBox="0 0 100 100"
            className="w-20 h-20 mx-auto"
          >
            {/* Lotus petals with cool teal */}
            {[...Array(8)].map((_, i) => {
              const angle = (i * 45 * Math.PI) / 180
              const cx = 50 + Math.cos(angle) * 20
              const cy = 50 + Math.sin(angle) * 20
              return (
                <motion.ellipse
                  key={i}
                  cx={cx}
                  cy={cy}
                  rx="12"
                  ry="6"
                  fill="none"
                  stroke="#7ec8c8"
                  strokeWidth="1"
                  transform={`rotate(${i * 45 + 90} ${cx} ${cy})`}
                  initial={{ opacity: 0, scale: 0 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ delay: i * 0.1, duration: 0.3 }}
                />
              )
            })}
            <circle cx="50" cy="50" r="8" fill="#a78bfa" opacity="0.3" />
          </svg>
        </motion.div>

        {/* Sequence name */}
        <motion.h2
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="text-2xl font-light text-[#f0f0f0] mb-2"
          style={{ fontFamily: "'Cinzel', serif" }}
        >
          {config.sequenceName}
        </motion.h2>
        <p
          className="text-[#9ca3af] mb-8"
          style={{ fontFamily: "'Crimson Pro', serif" }}
        >
          {config.flowSubtitle}
        </p>

        {/* Loading message */}
        <motion.p
          key={messageIndex}
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -10 }}
          className="text-[#9ca3af] mb-6"
          style={{ fontFamily: "'Crimson Pro', serif" }}
        >
          {preparingMessages[messageIndex]}
        </motion.p>

        {/* Progress bar */}
        <div className="w-full h-1 bg-[rgba(126,200,200,0.15)] rounded-full overflow-hidden">
          <motion.div
            className="h-full rounded-full"
            style={{ background: `linear-gradient(90deg, #7ec8c8, #a78bfa)` }}
            initial={{ width: 0 }}
            animate={{ width: `${progress}%` }}
            transition={{ duration: 0.1 }}
          />
        </div>
      </div>
    </div>
  )
}
