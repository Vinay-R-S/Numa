"use client"

import React, { useState } from "react"
import { motion } from "framer-motion"
import { Heart, Sparkles } from "lucide-react"

interface ReflectionCardProps {
  onComplete: () => void
}

const reflectionPrompts = [
  "How does your body feel right now?",
  "What thoughts came up during your practice?",
  "What are you grateful for in this moment?",
  "Is there anything you want to let go of?",
]

export function ReflectionCard({ onComplete }: ReflectionCardProps) {
  const [currentPrompt, setCurrentPrompt] = useState(0)
  const [reflection, setReflection] = useState("")

  const handleNext = () => {
    if (currentPrompt < reflectionPrompts.length - 1) {
      setCurrentPrompt(currentPrompt + 1)
      setReflection("")
    } else {
      onComplete()
    }
  }

  const handleSkip = () => {
    onComplete()
  }

  return (
    <div className="min-h-screen bg-[#0d0f14] flex items-center justify-center p-6">
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.5 }}
        className="max-w-lg w-full"
      >
        {/* Congratulations header */}
        <div className="text-center mb-8">
          <motion.div
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{ delay: 0.2, type: "spring", stiffness: 200 }}
            className="w-16 h-16 mx-auto mb-4 rounded-full bg-gradient-to-r from-[#7ec8c8] to-[#a78bfa] flex items-center justify-center"
          >
            <Sparkles className="w-8 h-8 text-[#0d0f14]" />
          </motion.div>
          <h2
            className="text-3xl font-light text-[#f0f0f0] mb-2"
            style={{ fontFamily: "'Cinzel', serif" }}
          >
            Beautiful Practice
          </h2>
          <p className="text-[#9ca3af]" style={{ fontFamily: "'Crimson Pro', serif" }}>
            Take a moment to reflect on your experience
          </p>
        </div>

        {/* Reflection card */}
        <motion.div
          key={currentPrompt}
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          className="rounded-2xl p-6 mb-6"
          style={{
            background: "rgba(255, 255, 255, 0.03)",
            backdropFilter: "blur(12px)",
            border: "1px solid rgba(255, 255, 255, 0.08)",
          }}
        >
          {/* Progress dots */}
          <div className="flex justify-center gap-2 mb-6">
            {reflectionPrompts.map((_, i) => (
              <div
                key={i}
                className={`w-2 h-2 rounded-full transition-colors duration-300 ${
                  i === currentPrompt ? "bg-[#7ec8c8]" : i < currentPrompt ? "bg-[#7ec8c8]/50" : "bg-[rgba(126,200,200,0.15)]"
                }`}
              />
            ))}
          </div>

          {/* Prompt */}
          <h3
            className="text-xl text-[#f0f0f0] text-center mb-6"
            style={{ fontFamily: "'Crimson Pro', serif" }}
          >
            {reflectionPrompts[currentPrompt]}
          </h3>

          {/* Text area */}
          <textarea
            value={reflection}
            onChange={(e) => setReflection(e.target.value)}
            placeholder="Write your thoughts here... (optional)"
            className="w-full h-32 bg-[#0d0f14] border border-[rgba(255,255,255,0.08)] rounded-xl p-4 text-[#f0f0f0] placeholder-[#9ca3af]/60 resize-none focus:outline-none focus:border-[#7ec8c8]/50 transition-colors duration-300"
            style={{ fontFamily: "'Crimson Pro', serif" }}
          />
        </motion.div>

        {/* Actions */}
        <div className="flex gap-4">
          <motion.button
            onClick={handleSkip}
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            className="flex-1 py-3 rounded-xl text-[#9ca3af] hover:text-[#f0f0f0] transition-colors duration-300"
            style={{
              fontFamily: "'Cinzel', serif",
              background: "rgba(255, 255, 255, 0.03)",
              backdropFilter: "blur(12px)",
              border: "1px solid rgba(255, 255, 255, 0.08)",
            }}
          >
            Skip Reflection
          </motion.button>
          <motion.button
            onClick={handleNext}
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            className="flex-1 py-3 rounded-xl bg-gradient-to-r from-[#7ec8c8] to-[#a78bfa] text-[#0d0f14] font-medium flex items-center justify-center gap-2"
            style={{ fontFamily: "'Cinzel', serif" }}
          >
            {currentPrompt < reflectionPrompts.length - 1 ? (
              "Next →"
            ) : (
              <>
                <Heart className="w-4 h-4" /> Complete
              </>
            )}
          </motion.button>
        </div>

        {/* Namaste message */}
        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.5 }}
          className="text-center text-[#9ca3af] text-sm mt-8"
          style={{ fontFamily: "'Noto Serif Devanagari', serif" }}
        >
          🙏 नमस्ते — The light in me honors the light in you
        </motion.p>
      </motion.div>
    </div>
  )
}
