"use client"

import React, { useState } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { X } from "lucide-react"
import { moodConfig, MoodType, getPosesForMood, PoseWithMoodReason } from "../yogaData"

interface YogaSectionProps {
  mood: MoodType
  onBeginSession: () => void
}

// Lotus divider component - thin line with centered lotus SVG
function LotusDivider() {
  return (
    <div className="flex items-center gap-4 my-6">
      <div className="flex-1 h-px bg-gradient-to-r from-transparent via-[rgba(126,200,200,0.2)] to-[rgba(167,139,250,0.2)]" />
      <svg width="20" height="12" viewBox="0 0 20 12" fill="none" className="flex-shrink-0 opacity-40">
        {/* Center petal */}
        <path
          d="M10 0C10 0 8 4 10 8C12 4 10 0 10 0Z"
          fill="url(#lotus-gradient)"
        />
        {/* Left petals */}
        <path
          d="M10 8C6 6 3 8 2 10C4 9 7 9 10 8Z"
          fill="url(#lotus-gradient)"
          opacity="0.8"
        />
        <path
          d="M10 7C7 5 4 6 2 7C5 7 8 7 10 7Z"
          fill="url(#lotus-gradient)"
          opacity="0.6"
        />
        {/* Right petals */}
        <path
          d="M10 8C14 6 17 8 18 10C16 9 13 9 10 8Z"
          fill="url(#lotus-gradient)"
          opacity="0.8"
        />
        <path
          d="M10 7C13 5 16 6 18 7C15 7 12 7 10 7Z"
          fill="url(#lotus-gradient)"
          opacity="0.6"
        />
        <defs>
          <linearGradient id="lotus-gradient" x1="0" y1="0" x2="20" y2="12">
            <stop offset="0%" stopColor="#7ec8c8" />
            <stop offset="100%" stopColor="#a78bfa" />
          </linearGradient>
        </defs>
      </svg>
      <div className="flex-1 h-px bg-gradient-to-r from-[rgba(167,139,250,0.2)] via-[rgba(126,200,200,0.2)] to-transparent" />
    </div>
  )
}

function DifficultyDots({ level }: { level: number }) {
  return (
    <div className="flex gap-1">
      {[...Array(5)].map((_, i) => (
        <span
          key={i}
          className={`w-1.5 h-1.5 rounded-full ${
            i < level ? "bg-[#7ec8c8]" : "bg-[rgba(126,200,200,0.15)]"
          }`}
        />
      ))}
    </div>
  )
}

// Pose image with fallback
function PoseCardImage({ pose }: { pose: PoseWithMoodReason }) {
  const [imageError, setImageError] = useState(false)

  if (imageError) {
    return (
      <div
        className="w-full flex items-center justify-center p-4"
        style={{
          height: "160px",
          background: "rgba(255, 255, 255, 0.03)",
          border: "1px solid rgba(255, 255, 255, 0.08)",
        }}
      >
        <span className="text-[#7ec8c8] text-sm text-center font-medium">
          {pose.englishName}
        </span>
      </div>
    )
  }

  return (
    <img
      src={pose.imageUrl}
      alt={pose.englishName}
      style={{ height: "160px", objectFit: "contain", width: "100%", backgroundColor: "rgba(0,0,0,0.2)" }}
      onError={() => setImageError(true)}
    />
  )
}

interface PoseCardProps {
  pose: PoseWithMoodReason
  onViewDetails: () => void
}

function PoseCard({ pose, onViewDetails }: PoseCardProps) {
  const [isHovered, setIsHovered] = useState(false)

  return (
    <motion.div
      className="flex-shrink-0 w-[200px] rounded-xl overflow-hidden cursor-pointer transition-all duration-300"
      style={{
        background: "rgba(255, 255, 255, 0.03)",
        backdropFilter: "blur(12px)",
        border: isHovered ? "1px solid rgba(126, 200, 200, 0.3)" : "1px solid rgba(255, 255, 255, 0.08)",
      }}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      onClick={onViewDetails}
      whileHover={{ y: -4 }}
      transition={{ duration: 0.3 }}
    >
      {/* Pose image */}
      <div className="relative h-40 rounded-t-xl overflow-hidden">
        <PoseCardImage pose={pose} />

        {/* Hover overlay */}
        <AnimatePresence>
          {isHovered && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.3 }}
              className="absolute inset-0 bg-[#0d0f14]/90 flex items-center justify-center p-4"
            >
              <p className="text-xs text-[#d1d5db] text-center line-clamp-4">
                {pose.benefits.substring(0, 120)}...
              </p>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Card content */}
      <div className="p-3">
        <h4 className="text-sm font-medium text-[#f0f0f0] mb-0.5">
          {pose.englishName}
        </h4>
        <p className="text-xs text-[#a78bfa] italic mb-2">
          {pose.sanskritName}
        </p>
        {/* Mood-specific reason */}
        <p className="text-[10px] text-[#9ca3af] italic mb-2 line-clamp-2">
          "{pose.moodReason}"
        </p>
        <div className="flex items-center justify-between">
          <DifficultyDots level={pose.difficulty} />
          <span className="text-xs text-[#9ca3af]">{pose.duration}</span>
        </div>
      </div>
    </motion.div>
  )
}

// Modal image with fallback
function ModalPoseImage({ pose }: { pose: PoseWithMoodReason }) {
  const [imageError, setImageError] = useState(false)

  if (imageError) {
    return (
      <div
        className="w-full h-full flex items-center justify-center"
        style={{
          background: "rgba(255, 255, 255, 0.03)",
        }}
      >
        <span className="text-[#7ec8c8] text-xl text-center font-medium">
          {pose.englishName}
        </span>
      </div>
    )
  }

  return (
    <img
      src={pose.imageUrl}
      alt={pose.englishName}
      className="w-full h-full"
      style={{ objectFit: "contain", backgroundColor: "rgba(0,0,0,0.3)" }}
      onError={() => setImageError(true)}
    />
  )
}

interface PoseDetailModalProps {
  pose: PoseWithMoodReason
  onClose: () => void
}

function PoseDetailModal({ pose, onClose }: PoseDetailModalProps) {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.3 }}
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70"
      onClick={onClose}
    >
      <motion.div
        initial={{ scale: 0.9, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        exit={{ scale: 0.9, opacity: 0 }}
        transition={{ duration: 0.3 }}
        className="rounded-2xl max-w-2xl w-full max-h-[85vh] overflow-y-auto"
        style={{
          background: "rgba(255, 255, 255, 0.03)",
          backdropFilter: "blur(12px)",
          border: "1px solid rgba(255, 255, 255, 0.08)",
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="relative h-56 rounded-t-2xl overflow-hidden">
          <ModalPoseImage pose={pose} />
          <div className="absolute inset-0 bg-gradient-to-t from-[#0d0f14] via-transparent to-transparent" />
          <button
            onClick={onClose}
            className="absolute top-4 right-4 p-2 rounded-full bg-black/50 text-[#f0f0f0] hover:bg-black/70 transition-colors duration-300"
          >
            <X className="w-5 h-5" />
          </button>
          <div className="absolute bottom-4 left-6 right-6">
            <h2
              className="text-2xl font-light text-[#f0f0f0] mb-1"
              style={{ fontFamily: "'Cinzel', serif" }}
            >
              {pose.englishName}
            </h2>
            <p className="text-[#a78bfa] italic" style={{ fontFamily: "'Noto Serif Devanagari', serif" }}>
              {pose.sanskritName}
            </p>
            <p className="text-xs text-[#9ca3af]">({pose.pronunciation})</p>
          </div>
        </div>

        {/* Content */}
        <div className="p-6">
          {/* Why this pose */}
          <div className="mb-6 p-4 rounded-lg bg-[#7ec8c8]/5 border border-[#7ec8c8]/20">
            <p className="text-sm text-[#7ec8c8] italic" style={{ fontFamily: "'Crimson Pro', serif" }}>
              "{pose.moodReason}"
            </p>
          </div>

          {/* Difficulty & Duration */}
          <div className="flex items-center gap-6 mb-2">
            <div>
              <p className="text-xs text-[#9ca3af] mb-1">Difficulty</p>
              <DifficultyDots level={pose.difficulty} />
            </div>
            <div>
              <p className="text-xs text-[#9ca3af] mb-1">Hold Duration</p>
              <p className="text-sm text-[#f0f0f0]">{pose.duration}</p>
            </div>
          </div>
          
          <LotusDivider />

          {/* Instructions */}
          <div className="mb-6">
            <h3 className="text-sm font-medium text-[#7ec8c8] mb-3">
              Instructions
            </h3>
            <ol className="space-y-2">
              {pose.instructions.map((step, i) => (
                <li key={i} className="flex gap-3 text-sm text-[#d1d5db]">
                  <span className="text-[#a78bfa] font-medium shrink-0">
                    {i + 1}.
                  </span>
                  <span>{step}</span>
                </li>
              ))}
            </ol>
          </div>

          <LotusDivider />

          {/* Benefits */}
          <div>
            <h3 className="text-sm font-medium text-[#7ec8c8] mb-3">
              Benefits
            </h3>
            <p className="text-sm text-[#d1d5db] leading-relaxed">
              {pose.benefits}
            </p>
          </div>
        </div>
      </motion.div>
    </motion.div>
  )
}

export function YogaSection({ mood, onBeginSession }: YogaSectionProps) {
  const [selectedPose, setSelectedPose] = useState<PoseWithMoodReason | null>(null)
  const config = moodConfig[mood]
  const poses = getPosesForMood(mood)

  return (
    <div className="flex-1 min-w-0">
      {/* Header */}
      <div className="mb-6">
        <h2
          className="text-2xl font-light text-[#f0f0f0] mb-1"
          style={{ fontFamily: "'Cinzel', serif" }}
        >
          {config.sequenceName}
        </h2>
        <p className="text-[#9ca3af]" style={{ fontFamily: "'Crimson Pro', serif" }}>
          — {config.flowSubtitle}
        </p>
      </div>

      {/* Scrollable pose cards */}
      <div className="relative mb-8">
        <div className="flex gap-4 overflow-x-auto pb-4 scrollbar-thin scrollbar-thumb-[rgba(126,200,200,0.3)] scrollbar-track-transparent">
          {poses.map((pose) => (
            <PoseCard
              key={pose.id}
              pose={pose}
              onViewDetails={() => setSelectedPose(pose)}
            />
          ))}
        </div>
        {/* Fade edges */}
        <div className="absolute right-0 top-0 bottom-4 w-16 bg-gradient-to-l from-[#0d0f14] to-transparent pointer-events-none" />
      </div>

      {/* Begin Session button */}
      <motion.button
        onClick={onBeginSession}
        whileHover={{ scale: 1.03 }}
        whileTap={{ scale: 0.98 }}
        className="group relative px-8 py-3 rounded-full bg-gradient-to-r from-[#7ec8c8] to-[#a78bfa] text-[#0d0f14] font-medium transition-all duration-300 hover:shadow-[0_0_30px_rgba(126,200,200,0.4)]"
        style={{ fontFamily: "'Cinzel', serif" }}
      >
        <span className="relative z-10">Begin Session →</span>
        <div className="absolute inset-0 rounded-full bg-gradient-to-r from-[#7ec8c8] to-[#a78bfa] blur-lg opacity-40 group-hover:opacity-60 transition-opacity duration-300" />
      </motion.button>

      {/* Pose detail modal */}
      <AnimatePresence>
        {selectedPose && (
          <PoseDetailModal
            pose={selectedPose}
            onClose={() => setSelectedPose(null)}
          />
        )}
      </AnimatePresence>
    </div>
  )
}
