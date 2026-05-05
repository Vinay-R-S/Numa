"use client"

import React, { useState, useRef, useEffect, useCallback } from "react"
import { Volume2, VolumeX, Play, Pause, SkipForward, SkipBack, Repeat, Repeat1 } from "lucide-react"
import { Button } from "@/components/ui/button"

interface Soundscape {
  id: string
  name: string
  description: string
  frequency: number
  duration: number
}

const soundscapes: Soundscape[] = [
  { id: "rain", name: "Gentle Rain", description: "Soft rainfall on leaves", frequency: 130, duration: 300 },
  { id: "forest", name: "Forest Morning", description: "Birds and distant streams", frequency: 174, duration: 300 },
  { id: "ocean", name: "Ocean Waves", description: "Rhythmic waves on shore", frequency: 136, duration: 300 },
  { id: "bowls", name: "Tibetan Bowls", description: "Singing bowls resonance", frequency: 528, duration: 300 },
  { id: "binaural", name: "Binaural Focus", description: "40Hz gamma binaural beat", frequency: 200, duration: 300 },
]

function formatTime(seconds: number): string {
  const m = Math.floor(seconds / 60)
  const s = Math.floor(seconds % 60)
  return `${m}:${s.toString().padStart(2, "0")}`
}

export function MusicPlayer() {
  const [activeSoundscape, setActiveSoundscape] = useState<Soundscape | null>(null)
  const [isPlaying, setIsPlaying] = useState(false)
  const [isMuted, setIsMuted] = useState(false)
  const [isLooping, setIsLooping] = useState(true)
  const [volume, setVolume] = useState(0.5)
  const [elapsed, setElapsed] = useState(0)

  const audioContextRef = useRef<AudioContext | null>(null)
  const oscillatorRef = useRef<OscillatorNode | null>(null)
  const gainRef = useRef<GainNode | null>(null)
  const binauralOscRef = useRef<OscillatorNode | null>(null)
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const startTimeRef = useRef(0)

  const stopOscillator = useCallback(() => {
    if (timerRef.current) {
      clearInterval(timerRef.current)
      timerRef.current = null
    }
    if (oscillatorRef.current) {
      try { oscillatorRef.current.stop() } catch {}
      oscillatorRef.current = null
    }
    if (binauralOscRef.current) {
      try { binauralOscRef.current.stop() } catch {}
      binauralOscRef.current = null
    }
    if (audioContextRef.current) {
      audioContextRef.current.close()
      audioContextRef.current = null
    }
    gainRef.current = null
  }, [])

  const startOscillator = useCallback(() => {
    if (!activeSoundscape) return
    stopOscillator()

    const AudioContextClass = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext
    if (!AudioContextClass) return

    const ctx = new AudioContextClass()
    audioContextRef.current = ctx

    const gain = ctx.createGain()
    gain.gain.setValueAtTime(isMuted ? 0 : volume * 0.04, ctx.currentTime)
    gain.connect(ctx.destination)
    gainRef.current = gain

    const osc = ctx.createOscillator()
    osc.type = "sine"
    osc.frequency.setValueAtTime(activeSoundscape.frequency, ctx.currentTime)
    osc.connect(gain)
    osc.start()
    oscillatorRef.current = osc

    if (activeSoundscape.id === "binaural") {
      const osc2 = ctx.createOscillator()
      osc2.type = "sine"
      osc2.frequency.setValueAtTime(activeSoundscape.frequency + 40, ctx.currentTime)
      osc2.connect(gain)
      osc2.start()
      binauralOscRef.current = osc2
    }

    startTimeRef.current = Date.now() - elapsed * 1000
    timerRef.current = setInterval(() => {
      const now = Date.now()
      const newElapsed = (now - startTimeRef.current) / 1000
      if (newElapsed >= activeSoundscape.duration) {
        if (isLooping) {
          startTimeRef.current = Date.now()
          setElapsed(0)
        } else {
          setIsPlaying(false)
          setElapsed(0)
        }
      } else {
        setElapsed(newElapsed)
      }
    }, 250)
  }, [activeSoundscape, isMuted, volume, elapsed, isLooping, stopOscillator])

  useEffect(() => {
    if (isPlaying && activeSoundscape) {
      startOscillator()
    } else {
      stopOscillator()
    }
    return stopOscillator
  }, [isPlaying, activeSoundscape?.id])

  useEffect(() => {
    if (gainRef.current && audioContextRef.current) {
      gainRef.current.gain.setValueAtTime(
        isMuted ? 0 : volume * 0.04,
        audioContextRef.current.currentTime
      )
    }
  }, [isMuted, volume])

  const handleSelectSoundscape = (soundscape: Soundscape) => {
    if (activeSoundscape?.id === soundscape.id) {
      setIsPlaying(!isPlaying)
    } else {
      stopOscillator()
      setElapsed(0)
      setActiveSoundscape(soundscape)
      setIsPlaying(true)
    }
  }

  const handleSeek = (delta: number) => {
    if (!activeSoundscape) return
    const newElapsed = Math.max(0, Math.min(activeSoundscape.duration, elapsed + delta))
    setElapsed(newElapsed)
    startTimeRef.current = Date.now() - newElapsed * 1000
  }

  const handleProgressClick = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!activeSoundscape) return
    const rect = e.currentTarget.getBoundingClientRect()
    const ratio = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width))
    const newElapsed = ratio * activeSoundscape.duration
    setElapsed(newElapsed)
    startTimeRef.current = Date.now() - newElapsed * 1000
  }

  const duration = activeSoundscape?.duration || 300
  const progress = duration > 0 ? (elapsed / duration) * 100 : 0

  return (
    <div className="w-full max-w-[300px] overflow-hidden rounded-2xl border border-border/40 bg-card/40">
      {/* Now playing / idle */}
      <div className="relative h-[120px] overflow-hidden bg-linear-to-b from-primary/5 to-background flex items-center justify-center">
        {activeSoundscape && isPlaying ? (
          <div className="text-center">
            <div className="mx-auto mb-2 flex h-12 w-12 items-center justify-center rounded-full border border-primary/30 bg-primary/10 animate-pulse">
              <Volume2 className="h-6 w-6 text-primary" />
            </div>
            <p className="text-sm font-medium text-foreground">{activeSoundscape.name}</p>
            <p className="text-xs text-muted-foreground">{activeSoundscape.description}</p>
          </div>
        ) : activeSoundscape ? (
          <div className="text-center">
            <div className="mx-auto mb-2 flex h-12 w-12 items-center justify-center rounded-full border border-border/40 bg-card/40">
              <Pause className="h-6 w-6 text-muted-foreground" />
            </div>
            <p className="text-sm font-medium text-foreground">{activeSoundscape.name}</p>
            <p className="text-xs text-muted-foreground">Paused</p>
          </div>
        ) : (
          <div className="text-center">
            <div className="mx-auto mb-2 flex h-12 w-12 items-center justify-center rounded-full border border-border/40 bg-card/40">
              <Volume2 className="h-6 w-6 text-muted-foreground" />
            </div>
            <p className="text-sm text-muted-foreground">Select a soundscape</p>
          </div>
        )}
      </div>

      <div className="p-3 sm:p-4 space-y-3">
        {/* Progress bar */}
        {activeSoundscape && (
          <div className="space-y-1">
            <div
              className="h-1.5 w-full rounded-full bg-border/30 cursor-pointer overflow-hidden"
              onClick={handleProgressClick}
            >
              <div
                className="h-full rounded-full bg-primary transition-all"
                style={{ width: `${progress}%` }}
              />
            </div>
            <div className="flex justify-between text-[10px] text-muted-foreground tabular-nums">
              <span>{formatTime(elapsed)}</span>
              <span>{formatTime(duration)}</span>
            </div>
          </div>
        )}

        {/* Transport controls */}
        {activeSoundscape && (
          <div className="flex items-center justify-center gap-1">
            <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => handleSeek(-1)} title="-1s">
              <SkipBack className="h-3.5 w-3.5" />
            </Button>
            <Button
              size="icon"
              className="h-10 w-10 rounded-full"
              onClick={() => setIsPlaying(!isPlaying)}
            >
              {isPlaying ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}
            </Button>
            <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => handleSeek(5)} title="+5s">
              <SkipForward className="h-3.5 w-3.5" />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              className={`h-8 w-8 ${isLooping ? "text-primary" : "text-muted-foreground"}`}
              onClick={() => setIsLooping(!isLooping)}
              title={isLooping ? "Loop on" : "Loop off"}
            >
              {isLooping ? <Repeat1 className="h-3.5 w-3.5" /> : <Repeat className="h-3.5 w-3.5" />}
            </Button>
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8"
              onClick={() => setIsMuted(!isMuted)}
            >
              {isMuted ? <VolumeX className="h-3.5 w-3.5" /> : <Volume2 className="h-3.5 w-3.5" />}
            </Button>
          </div>
        )}

        {/* Volume slider */}
        {activeSoundscape && (
          <div className="flex items-center gap-2">
            <VolumeX className="h-3 w-3 text-muted-foreground shrink-0" />
            <input
              type="range"
              min="0"
              max="1"
              step="0.01"
              value={isMuted ? 0 : volume}
              onChange={(e) => {
                const v = parseFloat(e.target.value)
                setVolume(v)
                if (v > 0 && isMuted) setIsMuted(false)
              }}
              className="w-full accent-primary h-1"
            />
            <Volume2 className="h-3 w-3 text-muted-foreground shrink-0" />
          </div>
        )}

        {/* Soundscape list */}
        <div className="space-y-1.5">
          {soundscapes.map((soundscape) => {
            const isActive = activeSoundscape?.id === soundscape.id
            return (
              <button
                key={soundscape.id}
                onClick={() => handleSelectSoundscape(soundscape)}
                className={`w-full rounded-lg border p-2.5 text-left transition-colors ${
                  isActive
                    ? "border-primary/40 bg-primary/10"
                    : "border-border/40 bg-card/20 hover:border-primary/20"
                }`}
              >
                <div className="flex items-center justify-between">
                  <div>
                    <p className={`text-xs font-medium ${isActive ? "text-primary" : "text-foreground"}`}>
                      {soundscape.name}
                    </p>
                    <p className="text-[10px] text-muted-foreground">
                      {soundscape.description}
                    </p>
                  </div>
                  {isActive && isPlaying && (
                    <div className="flex gap-0.5">
                      {[1, 2, 3].map((i) => (
                        <div
                          key={i}
                          className="w-0.5 rounded-full bg-primary animate-pulse"
                          style={{ height: `${6 + i * 2}px`, animationDelay: `${i * 100}ms` }}
                        />
                      ))}
                    </div>
                  )}
                </div>
              </button>
            )
          })}
        </div>
      </div>
    </div>
  )
}
