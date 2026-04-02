"use client"

import React, { useState } from "react"
import { motion } from "framer-motion"
import { MoodType, moodConfig } from "../yogaData"

interface MoodSelectorProps {
  onSelect: (mood: MoodType) => void
}

// Mood accent colors - cool palette
const moodColors: Record<MoodType, string> = {
  overwhelmed: "#7ec8c8",
  low: "#a78bfa",
  restless: "#60a5fa",
  numb: "#94a3b8",
  exhausted: "#6366f1",
}

// Overwhelmed: wavy lines SVG
function WavyLinesIcon({ color, isHovered }: { color: string; isHovered: boolean }) {
  return (
    <svg viewBox="0 0 60 60" className="w-[60px] h-[60px]">
      {[18, 30, 42].map((y, i) => (
        <motion.path
          key={i}
          d={`M 5 ${y} Q 15 ${y - 6}, 25 ${y} T 45 ${y} T 55 ${y}`}
          fill="none"
          stroke={color}
          strokeWidth="2"
          strokeLinecap="round"
          animate={{
            d: isHovered
              ? [
                  `M 5 ${y} Q 15 ${y - 8}, 25 ${y} T 45 ${y} T 55 ${y}`,
                  `M 5 ${y} Q 15 ${y + 8}, 25 ${y} T 45 ${y} T 55 ${y}`,
                  `M 5 ${y} Q 15 ${y - 8}, 25 ${y} T 45 ${y} T 55 ${y}`,
                ]
              : [
                  `M 5 ${y} Q 15 ${y - 4}, 25 ${y} T 45 ${y} T 55 ${y}`,
                  `M 5 ${y} Q 15 ${y + 4}, 25 ${y} T 45 ${y} T 55 ${y}`,
                  `M 5 ${y} Q 15 ${y - 4}, 25 ${y} T 45 ${y} T 55 ${y}`,
                ],
          }}
          transition={{
            duration: isHovered ? 0.8 : 2,
            repeat: Infinity,
            delay: i * 0.15,
          }}
        />
      ))}
    </svg>
  )
}

// Low: half sun rising
function SunIcon({ color, isHovered }: { color: string; isHovered: boolean }) {
  return (
    <svg viewBox="0 0 60 60" className="w-[60px] h-[60px]">
      {/* Horizon line */}
      <line x1="5" y1="40" x2="55" y2="40" stroke={color} strokeWidth="1.5" opacity="0.5" />
      {/* Sun circle */}
      <motion.g
        animate={{ y: isHovered ? -5 : 0 }}
        transition={{ duration: 0.6, ease: "easeOut" }}
      >
        <circle cx="30" cy="40" r="12" fill="none" stroke={color} strokeWidth="2" />
        {/* Sun rays */}
        {[...Array(5)].map((_, i) => {
          const angle = ((i - 2) * 30 * Math.PI) / 180 - Math.PI / 2
          const x1 = 30 + Math.cos(angle) * 16
          const y1 = 40 + Math.sin(angle) * 16
          const x2 = 30 + Math.cos(angle) * 22
          const y2 = 40 + Math.sin(angle) * 22
          if (y1 > 40) return null
          return (
            <line key={i} x1={x1} y1={y1} x2={x2} y2={y2} stroke={color} strokeWidth="2" strokeLinecap="round" />
          )
        })}
      </motion.g>
      {/* Mask below horizon */}
      <rect x="0" y="40" width="60" height="20" fill="#0d0f14" />
    </svg>
  )
}

// Restless: lightning bolt
function LightningIcon({ color, isHovered }: { color: string; isHovered: boolean }) {
  return (
    <svg viewBox="0 0 60 60" className="w-[60px] h-[60px]">
      <motion.path
        d="M 35 5 L 20 28 L 28 28 L 22 55 L 42 25 L 32 25 L 38 5 Z"
        fill="none"
        stroke={color}
        strokeWidth="2"
        strokeLinejoin="round"
        animate={{
          opacity: isHovered ? [1, 0.3, 1, 0.5, 1] : [1, 0.8, 1],
        }}
        transition={{
          duration: isHovered ? 0.3 : 2,
          repeat: Infinity,
        }}
      />
    </svg>
  )
}

// Numb: empty circle pulse
function CircleIcon({ color, isHovered }: { color: string; isHovered: boolean }) {
  return (
    <svg viewBox="0 0 60 60" className="w-[60px] h-[60px]">
      <motion.circle
        cx="30"
        cy="30"
        r="20"
        fill="none"
        stroke={color}
        strokeWidth="2"
        animate={{
          opacity: isHovered ? [1, 0.4, 1] : [0.6, 1, 0.6],
          scale: isHovered ? [1, 1.05, 1] : 1,
        }}
        transition={{
          duration: isHovered ? 0.6 : 3,
          repeat: Infinity,
        }}
      />
    </svg>
  )
}

// Exhausted: crescent moon
function MoonIcon({ color, isHovered }: { color: string; isHovered: boolean }) {
  return (
    <svg viewBox="0 0 60 60" className="w-[60px] h-[60px]">
      <motion.g
        animate={{
          rotate: isHovered ? [0, 15, 0] : [0, 8, 0],
          filter: isHovered ? "drop-shadow(0 0 6px rgba(74,126,110,0.5))" : "none",
        }}
        transition={{ duration: 3, repeat: Infinity, ease: "easeInOut" }}
        style={{ transformOrigin: "30px 30px" }}
      >
        <path
          d="M 38 15 A 18 18 0 1 1 38 45 A 14 14 0 1 0 38 15"
          fill="none"
          stroke={color}
          strokeWidth="2"
        />
      </motion.g>
    </svg>
  )
}

// Get icon component for mood
function MoodIcon({ mood, color, isHovered }: { mood: MoodType; color: string; isHovered: boolean }) {
  switch (mood) {
    case "overwhelmed":
      return <WavyLinesIcon color={color} isHovered={isHovered} />
    case "low":
      return <SunIcon color={color} isHovered={isHovered} />
    case "restless":
      return <LightningIcon color={color} isHovered={isHovered} />
    case "numb":
      return <CircleIcon color={color} isHovered={isHovered} />
    case "exhausted":
      return <MoonIcon color={color} isHovered={isHovered} />
    default:
      return null
  }
}

const moods: { type: MoodType; description: string }[] = [
  { type: "overwhelmed", description: "Mind racing, too much happening" },
  { type: "low", description: "Lacking energy or motivation" },
  { type: "restless", description: "Can't settle, fidgety energy" },
  { type: "numb", description: "Feeling disconnected or flat" },
  { type: "exhausted", description: "Deeply tired, need restoration" },
]

export function MoodSelector({ onSelect }: MoodSelectorProps) {
  const [hoveredMood, setHoveredMood] = useState<MoodType | null>(null)

  return (
    <div
      className="min-h-screen flex items-center justify-center p-6"
      style={{
        backgroundColor: "#0d0f14",
        backgroundImage: `
          radial-gradient(circle at 25% 25%, rgba(126,200,200,0.03) 0%, transparent 50%),
          radial-gradient(circle at 75% 75%, rgba(167,139,250,0.03) 0%, transparent 50%)
        `,
      }}
    >
      <div className="w-full max-w-6xl">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8 }}
          className="text-center mb-12"
        >
          <h2
            className="text-[3rem] font-light mb-3"
            style={{
              fontFamily: "'Cinzel', serif",
              fontWeight: 400,
              color: "#f0f0f0",
            }}
          >
            How are you feeling?
          </h2>
          <p
            className="text-[1.1rem]"
            style={{
              fontFamily: "'Crimson Pro', serif",
              fontStyle: "italic",
              color: "#9ca3af",
            }}
          >
            Select what resonates most with your current state
          </p>
        </motion.div>

        {/* Horizontal mood cards */}
        <div className="flex flex-row gap-4 justify-center flex-wrap">
          {moods.map((mood, index) => {
            const config = moodConfig[mood.type]
            const accentColor = moodColors[mood.type]
            const isHovered = hoveredMood === mood.type

            return (
              <motion.button
                key={mood.type}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.6, delay: index * 0.1 }}
                onMouseEnter={() => setHoveredMood(mood.type)}
                onMouseLeave={() => setHoveredMood(null)}
                onClick={() => onSelect(mood.type)}
                whileHover={{ y: -8 }}
                whileTap={{ scale: 0.97 }}
                className="relative flex-1 min-w-[180px] max-w-[200px] text-center cursor-pointer transition-all duration-400"
                style={{
                  background: "rgba(255, 255, 255, 0.03)",
                  backdropFilter: "blur(12px)",
                  border: `1px solid ${isHovered ? accentColor : "rgba(255, 255, 255, 0.08)"}`,
                  borderRadius: "16px",
                  padding: "2rem 1.5rem",
                }}
              >
                {/* Icon */}
                <div className="flex justify-center mb-4">
                  <MoodIcon mood={mood.type} color={accentColor} isHovered={isHovered} />
                </div>

                {/* Mood name */}
                <h3
                  className="text-[1.1rem] mb-2"
                  style={{
                    fontFamily: "'Cinzel', serif",
                    color: accentColor,
                  }}
                >
                  {config.label}
                </h3>

                {/* Description */}
                <p
                  className="text-[0.85rem]"
                  style={{
                    fontFamily: "'Crimson Pro', serif",
                    fontStyle: "italic",
                    color: "#9ca3af",
                  }}
                >
                  {mood.description}
                </p>
              </motion.button>
            )
          })}
        </div>
      </div>
    </div>
  )
}
