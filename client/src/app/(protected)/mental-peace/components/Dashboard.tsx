"use client"

import React, { useState } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { ChevronDown } from "lucide-react"
import { MoodType, moodConfig } from "../yogaData"
import { MeditationTimer } from "./MeditationTimer"
import { MusicPlayer } from "./MusicPlayer"
import { YogaSection } from "./YogaSection"

interface DashboardProps {
  mood: MoodType
  onBeginSession: () => void
}

// Lotus divider component - thin line with centered lotus SVG
function LotusDivider() {
  return (
    <div className="flex items-center gap-4 my-6">
      <div className="flex-1 h-px bg-gradient-to-r from-transparent via-[rgba(126,200,200,0.15)] to-[rgba(167,139,250,0.15)]" />
      <svg width="20" height="12" viewBox="0 0 20 12" fill="none" className="flex-shrink-0 opacity-30">
        {/* Center petal */}
        <path
          d="M10 0C10 0 8 4 10 8C12 4 10 0 10 0Z"
          fill="url(#dashboard-lotus-gradient)"
        />
        {/* Left petals */}
        <path
          d="M10 8C6 6 3 8 2 10C4 9 7 9 10 8Z"
          fill="url(#dashboard-lotus-gradient)"
          opacity="0.8"
        />
        <path
          d="M10 7C7 5 4 6 2 7C5 7 8 7 10 7Z"
          fill="url(#dashboard-lotus-gradient)"
          opacity="0.6"
        />
        {/* Right petals */}
        <path
          d="M10 8C14 6 17 8 18 10C16 9 13 9 10 8Z"
          fill="url(#dashboard-lotus-gradient)"
          opacity="0.8"
        />
        <path
          d="M10 7C13 5 16 6 18 7C15 7 12 7 10 7Z"
          fill="url(#dashboard-lotus-gradient)"
          opacity="0.6"
        />
        <defs>
          <linearGradient id="dashboard-lotus-gradient" x1="0" y1="0" x2="20" y2="12">
            <stop offset="0%" stopColor="#7ec8c8" />
            <stop offset="100%" stopColor="#a78bfa" />
          </linearGradient>
        </defs>
      </svg>
      <div className="flex-1 h-px bg-gradient-to-r from-[rgba(167,139,250,0.15)] via-[rgba(126,200,200,0.15)] to-transparent" />
    </div>
  )
}

export function Dashboard({ mood, onBeginSession }: DashboardProps) {
  const [showWhyPoses, setShowWhyPoses] = useState(false)
  const config = moodConfig[mood]

  return (
    <div
      className="min-h-screen p-6 lg:p-10"
      style={{
        backgroundColor: "#0d0f14",
        backgroundImage: `
          radial-gradient(circle at 25% 25%, rgba(126,200,200,0.03) 0%, transparent 50%),
          radial-gradient(circle at 75% 75%, rgba(167,139,250,0.03) 0%, transparent 50%)
        `,
      }}
    >
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          className="mb-8"
        >
          <h1
            className="text-3xl font-light mb-2"
            style={{
              fontFamily: "'Cinzel', serif",
              fontWeight: 400,
              color: "#f0f0f0",
            }}
          >
            Your Session
          </h1>
          <p
            style={{
              fontFamily: "'Crimson Pro', serif",
              color: "#9ca3af",
            }}
          >
            Take your time. Start with music, set a timer, or dive straight into the flow.
          </p>

          {/* Why these poses collapsible */}
          <div className="mt-4">
            <button
              onClick={() => setShowWhyPoses(!showWhyPoses)}
              className="flex items-center gap-1.5 text-sm transition-colors duration-300"
              style={{ color: showWhyPoses ? "#7ec8c8" : "#9ca3af" }}
            >
              <span style={{ fontFamily: "'Crimson Pro', serif" }}>Why these poses?</span>
              <motion.span
                animate={{ rotate: showWhyPoses ? 180 : 0 }}
                transition={{ duration: 0.3 }}
              >
                <ChevronDown className="w-4 h-4" />
              </motion.span>
            </button>

            <AnimatePresence>
              {showWhyPoses && (
                <motion.div
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: "auto", opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                  transition={{ duration: 0.4, ease: [0.25, 0.1, 0.25, 1] }}
                  className="overflow-hidden"
                >
                  <p
                    className="mt-3 text-sm leading-relaxed max-w-2xl pl-4"
                    style={{
                      fontFamily: "'Crimson Pro', serif",
                      color: "#9ca3af",
                      borderLeft: "2px solid rgba(126,200,200,0.3)",
                    }}
                  >
                    {config.therapeuticReason}
                  </p>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </motion.div>

        <LotusDivider />

        {/* Main layout */}
        <div className="flex flex-col lg:flex-row gap-6">
          {/* Left column - Music Player */}
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.6, delay: 0.1 }}
            className="lg:w-auto"
          >
            <MusicPlayer />
          </motion.div>

          {/* Center - Yoga Section */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.2 }}
            className="flex-1 min-w-0"
          >
            <YogaSection mood={mood} onBeginSession={onBeginSession} />
          </motion.div>

          {/* Right column - Meditation Timer */}
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.6, delay: 0.3 }}
            className="lg:w-auto"
          >
            <MeditationTimer />
          </motion.div>
        </div>
      </div>
    </div>
  )
}
