"use client"

import React, { useState, useRef, useEffect } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { Volume2, VolumeX, Play, Pause } from "lucide-react"

interface Soundscape {
  id: string
  name: string
  description: string
  videoId: string
  frequency: number
}

const soundscapes: Soundscape[] = [
  {
    id: "rain",
    name: "Gentle Rain",
    description: "Soft rainfall on leaves",
    videoId: "q76bMs-NwRk",
    frequency: 130,
  },
  {
    id: "forest",
    name: "Forest Morning",
    description: "Birds and distant streams",
    videoId: "xNN7iTA57jM",
    frequency: 174,
  },
  {
    id: "ocean",
    name: "Ocean Waves",
    description: "Rhythmic waves on shore",
    videoId: "bn9F19Hi1Lk",
    frequency: 136,
  },
  {
    id: "bowls",
    name: "Tibetan Bowls",
    description: "Singing bowls resonance",
    videoId: "AOp8YjMp4_Q",
    frequency: 528,
  },
]

export function MusicPlayer() {
  const [activeSoundscape, setActiveSoundscape] = useState<Soundscape | null>(null)
  const [isPlaying, setIsPlaying] = useState(false)
  const [isMuted, setIsMuted] = useState(false)
  const [transitioning, setTransitioning] = useState(false)
  const audioContextRef = useRef<AudioContext | null>(null)
  const oscillatorRef = useRef<OscillatorNode | null>(null)
  const gainRef = useRef<GainNode | null>(null)

  // Initialize ambient audio
  useEffect(() => {
    if (!activeSoundscape || !isPlaying) {
      if (oscillatorRef.current) {
        try { oscillatorRef.current.stop() } catch {}
        oscillatorRef.current = null
      }
      return
    }

    const AudioContextClass = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext
    if (!AudioContextClass) return

    const ctx = new AudioContextClass()
    audioContextRef.current = ctx

    const osc = ctx.createOscillator()
    const gain = ctx.createGain()

    osc.type = "sine"
    osc.frequency.setValueAtTime(activeSoundscape.frequency, ctx.currentTime)
    gain.gain.setValueAtTime(isMuted ? 0 : 0.02, ctx.currentTime)

    osc.connect(gain)
    gain.connect(ctx.destination)
    osc.start()

    oscillatorRef.current = osc
    gainRef.current = gain

    return () => {
      try { osc.stop() } catch {}
      ctx.close()
    }
  }, [activeSoundscape, isPlaying, isMuted])

  // Update volume when muted changes
  useEffect(() => {
    if (gainRef.current && audioContextRef.current) {
      gainRef.current.gain.setValueAtTime(
        isMuted ? 0 : 0.02,
        audioContextRef.current.currentTime
      )
    }
  }, [isMuted])

  const handleSelectSoundscape = (soundscape: Soundscape) => {
    if (activeSoundscape?.id === soundscape.id) {
      setIsPlaying(!isPlaying)
    } else {
      // Crossfade transition
      setTransitioning(true)
      setTimeout(() => {
        setActiveSoundscape(soundscape)
        setIsPlaying(true)
        setTransitioning(false)
      }, 300)
    }
  }

  return (
    <div
      className="w-[300px] rounded-2xl overflow-hidden"
      style={{
        background: "rgba(255, 255, 255, 0.03)",
        backdropFilter: "blur(12px)",
        border: "1px solid rgba(255, 255, 255, 0.08)",
      }}
    >
      {/* Video background */}
      <div className="relative h-[200px] overflow-hidden" style={{ backgroundColor: "#0d0f14" }}>
        <AnimatePresence>
          {activeSoundscape && isPlaying && !transitioning && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.5 }}
              className="absolute inset-0"
            >
              <iframe
                className="absolute inset-0 w-[140%] h-[140%] -top-[20%] -left-[20%] pointer-events-none"
                src={`https://www.youtube.com/embed/${activeSoundscape.videoId}?autoplay=1&mute=1&loop=1&playlist=${activeSoundscape.videoId}&controls=0&showinfo=0&rel=0`}
                allow="autoplay"
                title="Ambient video"
                style={{ border: "none" }}
              />
            </motion.div>
          )}
        </AnimatePresence>

        {/* Placeholder when no video */}
        {(!activeSoundscape || !isPlaying) && (
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="text-center">
              <div
                className="w-14 h-14 mx-auto mb-3 rounded-full flex items-center justify-center"
                style={{ backgroundColor: "rgba(126,200,200,0.1)" }}
              >
                <Volume2 className="w-7 h-7" style={{ color: "#7ec8c8" }} />
              </div>
              <p
                className="text-sm"
                style={{
                  fontFamily: "'Crimson Pro', serif",
                  color: "#9ca3af",
                }}
              >
                Select a soundscape
              </p>
            </div>
          </div>
        )}

        {/* Dark gradient overlay */}
        <div
          className="absolute inset-0 pointer-events-none"
          style={{
            background: "linear-gradient(to top, rgba(13,15,20,0.95) 0%, rgba(13,15,20,0.3) 60%, transparent 100%)",
          }}
        />

        {/* Now playing info */}
        {activeSoundscape && (
          <div className="absolute bottom-4 left-4 right-4">
            <p
              className="font-medium text-base"
              style={{
                fontFamily: "'Cinzel', serif",
                color: "#f0f0f0",
              }}
            >
              {activeSoundscape.name}
            </p>
            <p
              className="text-sm"
              style={{
                fontFamily: "'Crimson Pro', serif",
                fontStyle: "italic",
                color: "#9ca3af",
              }}
            >
              {activeSoundscape.description}
            </p>
          </div>
        )}
      </div>

      {/* Controls */}
      <div className="p-4">
        {/* Soundscape list */}
        <div className="space-y-2 mb-4">
          {soundscapes.map((soundscape) => {
            const isActive = activeSoundscape?.id === soundscape.id
            return (
              <motion.button
                key={soundscape.id}
                onClick={() => handleSelectSoundscape(soundscape)}
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                className="w-full p-3 rounded-lg text-left transition-all duration-300"
                style={{
                  background: isActive ? "rgba(126,200,200,0.1)" : "rgba(255, 255, 255, 0.02)",
                  border: isActive ? "1px solid rgba(126,200,200,0.4)" : "1px solid rgba(255, 255, 255, 0.05)",
                }}
              >
                <div className="flex items-center justify-between">
                  <div>
                    <p
                      className="text-sm font-medium"
                      style={{
                        fontFamily: "'Cinzel', serif",
                        color: isActive ? "#7ec8c8" : "#f0f0f0",
                      }}
                    >
                      {soundscape.name}
                    </p>
                    <p
                      className="text-xs"
                      style={{
                        fontFamily: "'Crimson Pro', serif",
                        color: "#9ca3af",
                      }}
                    >
                      {soundscape.description}
                    </p>
                  </div>
                  {isActive && isPlaying && (
                    <div className="flex gap-0.5">
                      {[...Array(3)].map((_, i) => (
                        <motion.div
                          key={i}
                          className="w-1 rounded-full"
                          style={{ backgroundColor: "#7ec8c8" }}
                          animate={{ height: [8, 16, 8] }}
                          transition={{
                            duration: 0.5,
                            delay: i * 0.1,
                            repeat: Infinity,
                          }}
                        />
                      ))}
                    </div>
                  )}
                </div>
              </motion.button>
            )
          })}
        </div>

        {/* Playback controls */}
        {activeSoundscape && (
          <div className="flex gap-2">
            <motion.button
              onClick={() => setIsPlaying(!isPlaying)}
              whileHover={{ scale: 1.02, boxShadow: "0 0 20px rgba(126,200,200,0.3)" }}
              whileTap={{ scale: 0.98 }}
              className="flex-1 py-2.5 rounded-lg flex items-center justify-center gap-2"
              style={{
                fontFamily: "'Cinzel', serif",
                letterSpacing: "0.1em",
                fontSize: "0.875rem",
                background: "linear-gradient(135deg, #7ec8c8 0%, #6366f1 100%)",
                color: "white",
              }}
            >
              {isPlaying ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
              {isPlaying ? "PAUSE" : "PLAY"}
            </motion.button>
            <motion.button
              onClick={() => setIsMuted(!isMuted)}
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              className="p-2.5 rounded-lg transition-colors duration-300"
              style={{
                background: isMuted ? "rgba(99,102,241,0.2)" : "rgba(255, 255, 255, 0.02)",
                border: isMuted ? "1px solid rgba(99,102,241,0.5)" : "1px solid rgba(255, 255, 255, 0.08)",
                color: isMuted ? "#6366f1" : "#9ca3af",
              }}
            >
              {isMuted ? <VolumeX className="w-4 h-4" /> : <Volume2 className="w-4 h-4" />}
            </motion.button>
          </div>
        )}
      </div>
    </div>
  )
}
