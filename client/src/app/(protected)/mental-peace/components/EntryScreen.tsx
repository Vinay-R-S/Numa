"use client"

import React, { useEffect, useRef } from "react"
import { motion } from "framer-motion"
import { Headphones } from "lucide-react"

interface EntryScreenProps {
  onBegin: () => void
}

// Floating teal particle component
function FloatingParticle({ delay, duration, size, left }: { delay: number; duration: number; size: number; left: string }) {
  return (
    <motion.div
      className="absolute rounded-full"
      style={{
        width: size,
        height: size,
        left,
        bottom: -20,
        backgroundColor: "#7ec8c8",
        opacity: 0.15,
      }}
      animate={{
        y: [0, -900],
        opacity: [0, 0.15, 0],
      }}
      transition={{
        duration,
        delay,
        repeat: Infinity,
        ease: "linear",
      }}
    />
  )
}

// 4-pointed star/lotus motif SVG - Sarvam.ai inspired
function StarLotusMotif() {
  return (
    <motion.div
      initial={{ scale: 0, opacity: 0 }}
      animate={{ scale: 1, opacity: 1 }}
      transition={{ duration: 1.5, ease: "easeOut" }}
    >
      <motion.svg
        viewBox="0 0 120 120"
        className="w-[120px] h-[120px]"
        animate={{ rotate: 360 }}
        transition={{ duration: 60, repeat: Infinity, ease: "linear" }}
      >
        {/* 4-pointed star base */}
        <path
          d="M60 10 L68 52 L110 60 L68 68 L60 110 L52 68 L10 60 L52 52 Z"
          fill="none"
          stroke="#7ec8c8"
          strokeWidth="1"
          opacity="0.8"
        />
        {/* Inner diamond */}
        <path
          d="M60 30 L70 60 L60 90 L50 60 Z"
          fill="none"
          stroke="#7ec8c8"
          strokeWidth="1"
          opacity="0.6"
        />
        {/* Petal details on each point */}
        {[0, 90, 180, 270].map((angle) => (
          <g key={angle} transform={`rotate(${angle} 60 60)`}>
            <ellipse
              cx="60"
              cy="25"
              rx="6"
              ry="10"
              fill="none"
              stroke="#a78bfa"
              strokeWidth="0.8"
              opacity="0.5"
            />
          </g>
        ))}
        {/* Center circle */}
        <circle cx="60" cy="60" r="8" fill="none" stroke="#7ec8c8" strokeWidth="1" opacity="0.8" />
        {/* Center dot */}
        <circle cx="60" cy="60" r="3" fill="#7ec8c8" opacity="0.6" />
      </motion.svg>
    </motion.div>
  )
}

// Geometric grid/globe pattern - subtle background
function GeometricGrid() {
  return (
    <svg
      className="absolute inset-0 w-full h-full opacity-[0.03] pointer-events-none"
      preserveAspectRatio="xMidYMid slice"
    >
      <defs>
        <pattern id="grid" width="60" height="60" patternUnits="userSpaceOnUse">
          <path
            d="M 60 0 L 0 0 0 60"
            fill="none"
            stroke="#7ec8c8"
            strokeWidth="0.5"
          />
        </pattern>
        {/* Globe/sphere effect */}
        <radialGradient id="globeFade" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stopColor="white" stopOpacity="1" />
          <stop offset="70%" stopColor="white" stopOpacity="0.5" />
          <stop offset="100%" stopColor="white" stopOpacity="0" />
        </radialGradient>
        <mask id="globeMask">
          <rect width="100%" height="100%" fill="url(#globeFade)" />
        </mask>
      </defs>
      <rect width="100%" height="100%" fill="url(#grid)" mask="url(#globeMask)" />
      {/* Curved lines for globe effect */}
      {[...Array(5)].map((_, i) => {
        const offset = (i + 1) * 15
        return (
          <g key={i} opacity="0.5">
            <ellipse
              cx="50%"
              cy="50%"
              rx={`${30 + offset}%`}
              ry={`${15 + offset * 0.3}%`}
              fill="none"
              stroke="#7ec8c8"
              strokeWidth="0.3"
            />
          </g>
        )
      })}
    </svg>
  )
}

// Cool mandala watermark
function MandalaWatermark() {
  return (
    <svg
      viewBox="0 0 400 400"
      className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[700px] h-[700px] opacity-[0.04] pointer-events-none"
    >
      {/* 6 concentric circles */}
      {[40, 70, 100, 130, 160, 190].map((r, i) => (
        <circle
          key={`circle-${i}`}
          cx="200"
          cy="200"
          r={r}
          fill="none"
          stroke="#7ec8c8"
          strokeWidth="0.5"
        />
      ))}
      {/* 8 radial lines */}
      {[...Array(8)].map((_, i) => {
        const angle = (i * 45 * Math.PI) / 180
        const x1 = 200 + Math.cos(angle) * 40
        const y1 = 200 + Math.sin(angle) * 40
        const x2 = 200 + Math.cos(angle) * 190
        const y2 = 200 + Math.sin(angle) * 190
        return (
          <line
            key={`line-${i}`}
            x1={x1}
            y1={y1}
            x2={x2}
            y2={y2}
            stroke="#a78bfa"
            strokeWidth="0.5"
          />
        )
      })}
      {/* Diamond shapes at intersections */}
      {[40, 70, 100, 130, 160, 190].map((r) =>
        [...Array(8)].map((_, i) => {
          const angle = (i * 45 * Math.PI) / 180
          const cx = 200 + Math.cos(angle) * r
          const cy = 200 + Math.sin(angle) * r
          return (
            <path
              key={`diamond-${r}-${i}`}
              d={`M ${cx} ${cy - 4} L ${cx + 3} ${cy} L ${cx} ${cy + 4} L ${cx - 3} ${cy} Z`}
              fill="none"
              stroke="#7ec8c8"
              strokeWidth="0.5"
            />
          )
        })
      )}
    </svg>
  )
}

export function EntryScreen({ onBegin }: EntryScreenProps) {
  const audioContextRef = useRef<AudioContext | null>(null)
  const oscillatorsRef = useRef<OscillatorNode[]>([])
  const gainsRef = useRef<GainNode[]>([])

  // Initialize ambient Om frequency audio on mount
  useEffect(() => {
    const AudioContextClass = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext
    if (!AudioContextClass) return

    const ctx = new AudioContextClass()
    audioContextRef.current = ctx

    // First oscillator: 136.1Hz (Om frequency)
    const osc1 = ctx.createOscillator()
    const gain1 = ctx.createGain()
    const lfo1 = ctx.createOscillator()
    const lfoGain1 = ctx.createGain()

    osc1.type = "sine"
    osc1.frequency.setValueAtTime(136.1, ctx.currentTime)

    lfo1.type = "sine"
    lfo1.frequency.setValueAtTime(0.3, ctx.currentTime)
    lfoGain1.gain.setValueAtTime(0.005, ctx.currentTime)

    lfo1.connect(lfoGain1)
    lfoGain1.connect(gain1.gain)

    // Fade in over 3 seconds
    gain1.gain.setValueAtTime(0, ctx.currentTime)
    gain1.gain.linearRampToValueAtTime(0.015, ctx.currentTime + 3)

    osc1.connect(gain1)
    gain1.connect(ctx.destination)
    osc1.start()
    lfo1.start()

    // Second oscillator: 272.2Hz (octave above)
    const osc2 = ctx.createOscillator()
    const gain2 = ctx.createGain()

    osc2.type = "sine"
    osc2.frequency.setValueAtTime(272.2, ctx.currentTime)

    gain2.gain.setValueAtTime(0, ctx.currentTime)
    gain2.gain.linearRampToValueAtTime(0.008, ctx.currentTime + 3)

    osc2.connect(gain2)
    gain2.connect(ctx.destination)
    osc2.start()

    oscillatorsRef.current = [osc1, osc2, lfo1]
    gainsRef.current = [gain1, gain2]

    return () => {
      oscillatorsRef.current.forEach((osc) => {
        try { osc.stop() } catch {}
      })
      ctx.close()
    }
  }, [])

  const handleBegin = () => {
    // Fade out audio smoothly
    if (audioContextRef.current) {
      const ctx = audioContextRef.current
      gainsRef.current.forEach((gain) => {
        gain.gain.linearRampToValueAtTime(0, ctx.currentTime + 0.5)
      })
    }

    setTimeout(() => {
      oscillatorsRef.current.forEach((osc) => {
        try { osc.stop() } catch {}
      })
      audioContextRef.current?.close()
      onBegin()
    }, 500)
  }

  return (
    <div
      className="relative min-h-screen flex items-center justify-center overflow-hidden"
      style={{
        backgroundColor: "#0d0f14",
        backgroundImage: `
          linear-gradient(135deg, #0d0f14 0%, #151a24 50%, #0d0f14 100%),
          radial-gradient(circle at 25% 25%, rgba(126,200,200,0.02) 0%, transparent 50%),
          radial-gradient(circle at 75% 75%, rgba(167,139,250,0.02) 0%, transparent 50%)
        `,
      }}
    >
      {/* Geometric grid pattern */}
      <GeometricGrid />

      {/* Teal glow top-right */}
      <div
        className="absolute top-0 right-0 w-[600px] h-[600px] rounded-full blur-[150px] pointer-events-none"
        style={{ backgroundColor: "rgba(126,200,200,0.08)" }}
      />

      {/* Purple glow bottom-left */}
      <div
        className="absolute bottom-0 left-0 w-[500px] h-[500px] rounded-full blur-[150px] pointer-events-none"
        style={{ backgroundColor: "rgba(167,139,250,0.06)" }}
      />

      {/* Floating teal particles */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        {[...Array(25)].map((_, i) => (
          <FloatingParticle
            key={i}
            delay={i * 0.6}
            duration={12 + Math.random() * 6}
            size={1 + Math.random() * 2}
            left={`${Math.random() * 100}%`}
          />
        ))}
      </div>

      {/* Mandala watermark */}
      <MandalaWatermark />

      {/* Content */}
      <div className="relative z-10 text-center px-6">
        {/* Star/Lotus motif */}
        <div className="mb-8">
          <StarLotusMotif />
        </div>

        {/* Devanagari Namaste */}
        <motion.p
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 0.8 }}
          className="text-[2.5rem] mb-2"
          style={{
            fontFamily: "'Noto Serif Devanagari', serif",
            color: "#7ec8c8",
            letterSpacing: "0.1em",
          }}
        >
          नमस्ते
        </motion.p>

        {/* English Namaste */}
        <motion.h1
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 1.2 }}
          className="text-[4rem] font-light mb-4"
          style={{
            fontFamily: "'Cinzel', serif",
            fontWeight: 300,
            color: "#f0f0f0",
            letterSpacing: "0.4em",
          }}
        >
          Namaste
        </motion.h1>

        {/* Subtitle */}
        <motion.p
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 1.8 }}
          className="text-[1.2rem] mb-12 max-w-md mx-auto"
          style={{
            fontFamily: "'Crimson Pro', serif",
            fontStyle: "italic",
            color: "#9ca3af",
          }}
        >
          Your space for stillness, breath, and healing
        </motion.p>

        {/* Begin button */}
        <motion.button
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 2.2 }}
          whileHover={{ scale: 1.02, boxShadow: "0 0 30px rgba(126,200,200,0.4)" }}
          whileTap={{ scale: 0.98 }}
          onClick={handleBegin}
          className="px-10 py-4 text-white transition-all duration-300"
          style={{
            fontFamily: "'Cinzel', serif",
            letterSpacing: "0.2em",
            background: "linear-gradient(135deg, #7ec8c8 0%, #6366f1 100%)",
            borderRadius: "4px",
            border: "none",
          }}
        >
          BEGIN YOUR PRACTICE
        </motion.button>

        {/* Headphones hint */}
        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.8, delay: 2.6 }}
          className="mt-8 flex items-center justify-center gap-2 text-sm"
          style={{ color: "#9ca3af" }}
        >
          <Headphones className="w-4 h-4" />
          Best experienced with headphones
        </motion.p>
      </div>
    </div>
  )
}
