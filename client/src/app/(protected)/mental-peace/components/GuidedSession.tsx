"use client"

import React, { useState, useEffect, useRef } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { X, ChevronLeft, ChevronRight, Play, Pause } from "lucide-react"
import { MoodType, getPosesForMood, PoseWithMoodReason } from "../yogaData"
import { BreathingGuide } from "./BreathingGuide"

interface GuidedSessionProps {
  mood: MoodType
  onEnd: () => void
}

// Pose image with fallback for guided session
function GuidedPoseImage({ pose }: { pose: PoseWithMoodReason }) {
  const [imageError, setImageError] = useState(false)

  if (imageError) {
    return (
      <div
        className="flex items-center justify-center rounded-2xl"
        style={{
          maxHeight: "350px",
          width: "100%",
          background: "rgba(255, 255, 255, 0.03)",
          border: "1px solid rgba(255, 255, 255, 0.08)",
          padding: "3rem",
        }}
      >
        <span className="text-[#7ec8c8] text-2xl font-medium text-center">
          {pose.englishName}
        </span>
      </div>
    )
  }

  return (
    <img
      src={pose.imageUrl}
      alt={pose.englishName}
      style={{ 
        maxHeight: "350px", 
        width: "100%", 
        objectFit: "contain",
        backgroundColor: "rgba(0,0,0,0.2)",
        borderRadius: "1rem"
      }}
      onError={() => setImageError(true)}
    />
  )
}

export function GuidedSession({ mood, onEnd }: GuidedSessionProps) {
  const poses = getPosesForMood(mood)
  const [currentIndex, setCurrentIndex] = useState(0)
  const [isPlaying, setIsPlaying] = useState(true)
  const [timeRemaining, setTimeRemaining] = useState(30)
  const intervalRef = useRef<NodeJS.Timeout | null>(null)

  const currentPose = poses[currentIndex]
  const progress = ((currentIndex + 1) / poses.length) * 100

  useEffect(() => {
    if (isPlaying && timeRemaining > 0) {
      intervalRef.current = setInterval(() => {
        setTimeRemaining((prev) => {
          if (prev <= 1) {
            if (currentIndex < poses.length - 1) {
              setCurrentIndex((i) => i + 1)
              return 30
            } else {
              setIsPlaying(false)
              onEnd()
              return 0
            }
          }
          return prev - 1
        })
      }, 1000)
    }

    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current)
    }
  }, [isPlaying, currentIndex, poses.length, onEnd, timeRemaining])

  const handlePrevious = () => {
    if (currentIndex > 0) {
      setCurrentIndex(currentIndex - 1)
      setTimeRemaining(30)
    }
  }

  const handleNext = () => {
    if (currentIndex < poses.length - 1) {
      setCurrentIndex(currentIndex + 1)
      setTimeRemaining(30)
    } else {
      onEnd()
    }
  }

  return (
    <div
      className="min-h-screen flex flex-col"
      style={{
        backgroundColor: "#0d0f14",
        backgroundImage: `
          radial-gradient(circle at 25% 25%, rgba(126,200,200,0.03) 0%, transparent 50%),
          radial-gradient(circle at 75% 75%, rgba(167,139,250,0.03) 0%, transparent 50%)
        `,
      }}
    >
      {/* Header */}
      <div
        className="flex items-center justify-between p-4"
        style={{ borderBottom: "1px solid rgba(255,255,255,0.08)" }}
      >
        <div className="flex items-center gap-4">
          <span
            className="text-sm"
            style={{
              fontFamily: "'Crimson Pro', serif",
              color: "#9ca3af",
            }}
          >
            Pose {currentIndex + 1} of {poses.length}
          </span>
          {/* Progress bar */}
          <div
            className="w-32 h-1 rounded-full overflow-hidden"
            style={{ backgroundColor: "rgba(126,200,200,0.2)" }}
          >
            <motion.div
              className="h-full rounded-full"
              style={{ background: "linear-gradient(90deg, #7ec8c8, #a78bfa)" }}
              animate={{ width: `${progress}%` }}
              transition={{ duration: 0.3 }}
            />
          </div>
        </div>
        <button
          onClick={onEnd}
          className="p-2 rounded-lg transition-colors duration-300"
          style={{ color: "#9ca3af" }}
          onMouseEnter={(e) => (e.currentTarget.style.color = "#f0f0f0")}
          onMouseLeave={(e) => (e.currentTarget.style.color = "#9ca3af")}
        >
          <X className="w-5 h-5" />
        </button>
      </div>

      {/* Main content */}
      <div className="flex-1 flex flex-col lg:flex-row">
        {/* Left side - Pose Image and Breathing Guide */}
        <div className="lg:w-1/2 flex flex-col items-center justify-center p-6 lg:p-10">
          <AnimatePresence mode="wait">
            <motion.div
              key={currentPose.id}
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.9 }}
              transition={{ duration: 0.6 }}
              className="w-full max-w-md aspect-[4/3] mb-8"
            >
              <GuidedPoseImage pose={currentPose} />
            </motion.div>
          </AnimatePresence>

          {/* Breathing Guide */}
          <div className="mt-4">
            <BreathingGuide isActive={isPlaying} />
          </div>
        </div>

        {/* Right side - Pose details */}
        <div className="lg:w-1/2 p-6 lg:p-10 flex flex-col justify-center">
          <AnimatePresence mode="wait">
            <motion.div
              key={currentPose.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              transition={{ duration: 0.6 }}
            >
              {/* Timer */}
              <div className="mb-6">
                <div
                  className="text-5xl font-light tabular-nums"
                  style={{
                    fontFamily: "'Cinzel', serif",
                    color: "#f0f0f0",
                  }}
                >
                  0:{timeRemaining.toString().padStart(2, "0")}
                </div>
                <p
                  className="text-sm mt-1"
                  style={{
                    fontFamily: "'Crimson Pro', serif",
                    color: "#9ca3af",
                  }}
                >
                  Hold this pose
                </p>
              </div>

              {/* Pose name */}
              <h2
                className="text-3xl font-light mb-1"
                style={{
                  fontFamily: "'Cinzel', serif",
                  fontWeight: 400,
                  color: "#f0f0f0",
                }}
              >
                {currentPose.englishName}
              </h2>
              <p
                className="mb-2"
                style={{
                  fontFamily: "'Crimson Pro', serif",
                  fontStyle: "italic",
                  color: "#7ec8c8",
                }}
              >
                {currentPose.sanskritName}
              </p>
              <p
                className="text-xs mb-6"
                style={{ color: "#9ca3af" }}
              >
                ({currentPose.pronunciation})
              </p>

              {/* Why this pose */}
              <div
                className="mb-6 p-4 rounded-lg"
                style={{
                  background: "rgba(126,200,200,0.05)",
                  border: "1px solid rgba(126,200,200,0.2)",
                }}
              >
                <p
                  className="text-sm"
                  style={{
                    fontFamily: "'Crimson Pro', serif",
                    fontStyle: "italic",
                    color: "#7ec8c8",
                  }}
                >
                  "{currentPose.moodReason}"
                </p>
              </div>

              {/* Current instruction */}
              <div className="mb-8">
                <h4
                  className="text-sm font-medium mb-2"
                  style={{
                    fontFamily: "'Cinzel', serif",
                    color: "#a78bfa",
                  }}
                >
                  Focus on:
                </h4>
                <p
                  style={{
                    fontFamily: "'Crimson Pro', serif",
                    color: "#f0f0f0",
                    lineHeight: 1.8,
                  }}
                >
                  {currentPose.instructions[Math.min(Math.floor((30 - timeRemaining) / 6), currentPose.instructions.length - 1)]}
                </p>
              </div>
            </motion.div>
          </AnimatePresence>

          {/* Controls */}
          <div className="flex items-center gap-4">
            <motion.button
              onClick={handlePrevious}
              disabled={currentIndex === 0}
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              className="p-3 rounded-lg disabled:opacity-30 disabled:cursor-not-allowed transition-colors duration-300"
              style={{
                background: "rgba(255, 255, 255, 0.03)",
                border: "1px solid rgba(255, 255, 255, 0.08)",
                color: "#9ca3af",
              }}
            >
              <ChevronLeft className="w-5 h-5" />
            </motion.button>

            <motion.button
              onClick={() => setIsPlaying(!isPlaying)}
              whileHover={{ scale: 1.02, boxShadow: "0 0 30px rgba(126,200,200,0.4)" }}
              whileTap={{ scale: 0.98 }}
              className="flex-1 py-3 rounded-lg text-white font-medium flex items-center justify-center gap-2"
              style={{
                fontFamily: "'Cinzel', serif",
                letterSpacing: "0.1em",
                background: "linear-gradient(135deg, #7ec8c8 0%, #6366f1 100%)",
              }}
            >
              {isPlaying ? (
                <>
                  <Pause className="w-5 h-5" /> PAUSE
                </>
              ) : (
                <>
                  <Play className="w-5 h-5" /> RESUME
                </>
              )}
            </motion.button>

            <motion.button
              onClick={handleNext}
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              className="p-3 rounded-lg transition-colors duration-300"
              style={{
                background: "rgba(255, 255, 255, 0.03)",
                border: "1px solid rgba(255, 255, 255, 0.08)",
                color: "#9ca3af",
              }}
            >
              <ChevronRight className="w-5 h-5" />
            </motion.button>
          </div>
        </div>
      </div>
    </div>
  )
}
