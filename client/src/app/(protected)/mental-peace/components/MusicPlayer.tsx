"use client"

import React, { useState, useRef, useEffect, useCallback } from "react"
import { Volume2, VolumeX, Play, Pause, SkipForward, SkipBack, Repeat, Repeat1, Loader2 } from "lucide-react"
import { Button } from "@/components/ui/button"

interface Soundscape {
  id: string
  name: string
  description: string
  src: string
  fallbackDuration: number
}

const soundscapes: Soundscape[] = [
  {
    id: "rain-thunder-birds",
    name: "Rain and Birds",
    description: "Rainfall with soft thunder and birds",
    src: "/api/audio/rain-thunder-birds.ogg",
    fallbackDuration: 134,
  },
  {
    id: "forest-ambience",
    name: "Forest Ambience",
    description: "Forest wind, birds, and insects",
    src: "/api/audio/forest-ambience.ogg",
    fallbackDuration: 123,
  },
  {
    id: "ocean-waves",
    name: "Ocean Waves",
    description: "Waves rolling over small stones",
    src: "/api/audio/ocean-waves.ogg",
    fallbackDuration: 120,
  },
  {
    id: "water-on-rocks",
    name: "Water on Rocks",
    description: "Shore water breaking on rocks",
    src: "/api/audio/water-on-rocks.ogg",
    fallbackDuration: 155,
  },
  {
    id: "yoga-flow",
    name: "Yoga Flow",
    description: "Layered forest and water ambience",
    src: "/api/audio/yoga-flow.ogg",
    fallbackDuration: 123,
  },
]

function formatTime(seconds: number): string {
  const safeSeconds = Number.isFinite(seconds) ? Math.max(0, seconds) : 0
  const m = Math.floor(safeSeconds / 60)
  const s = Math.floor(safeSeconds % 60)
  return `${m}:${s.toString().padStart(2, "0")}`
}

export function MusicPlayer() {
  const [activeSoundscape, setActiveSoundscape] = useState<Soundscape | null>(null)
  const [isPlaying, setIsPlaying] = useState(false)
  const [isMuted, setIsMuted] = useState(false)
  const [isLooping, setIsLooping] = useState(true)
  const [volume, setVolume] = useState(0.5)
  const [elapsed, setElapsed] = useState(0)
  const [duration, setDuration] = useState(0)
  const [isPreparing, setIsPreparing] = useState(true)
  const [audioError, setAudioError] = useState<string | null>(null)

  const audioRef = useRef<HTMLAudioElement | null>(null)
  const autoPlayPendingRef = useRef(false)

  useEffect(() => {
    let cancelled = false

    async function ensureAudioLibrary() {
      setIsPreparing(true)
      setAudioError(null)
      try {
        const res = await fetch("/api/audio-library/ensure", { method: "POST" })
        if (!res.ok) {
          throw new Error("Unable to prepare local audio")
        }

        const payload = await res.json()
        if (!payload.ok) {
          throw new Error("Some audio files could not be downloaded")
        }
      } catch (err) {
        if (!cancelled) {
          setAudioError(err instanceof Error ? err.message : "Unable to prepare local audio")
        }
      } finally {
        if (!cancelled) setIsPreparing(false)
      }
    }

    ensureAudioLibrary()

    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    const audio = audioRef.current
    if (!audio) return

    audio.volume = isMuted ? 0 : volume
  }, [isMuted, volume])

  useEffect(() => {
    const audio = audioRef.current
    if (!audio) return

    audio.loop = isLooping
  }, [isLooping])

  useEffect(() => {
    const audio = audioRef.current
    if (!audio) return

    const handleTimeUpdate = () => setElapsed(audio.currentTime)
    const handleLoadedMetadata = () => {
      const loadedDuration = Number.isFinite(audio.duration) ? audio.duration : activeSoundscape?.fallbackDuration || 0
      setDuration(loadedDuration)
    }
    const handleEnded = () => {
      setIsPlaying(false)
      setElapsed(0)
    }
    const handleError = () => {
      setIsPlaying(false)
      setAudioError("This local audio file is not ready yet")
    }

    audio.addEventListener("timeupdate", handleTimeUpdate)
    audio.addEventListener("loadedmetadata", handleLoadedMetadata)
    audio.addEventListener("ended", handleEnded)
    audio.addEventListener("error", handleError)

    return () => {
      audio.removeEventListener("timeupdate", handleTimeUpdate)
      audio.removeEventListener("loadedmetadata", handleLoadedMetadata)
      audio.removeEventListener("ended", handleEnded)
      audio.removeEventListener("error", handleError)
    }
  }, [activeSoundscape?.fallbackDuration])

  const playActiveAudio = useCallback(async () => {
    const audio = audioRef.current
    if (!audio || !activeSoundscape) return

    try {
      setAudioError(null)
      await audio.play()
      setIsPlaying(true)
    } catch {
      setIsPlaying(false)
      setAudioError("Unable to play this audio")
    }
  }, [activeSoundscape])

  useEffect(() => {
    const audio = audioRef.current
    if (!audio || !activeSoundscape) return

    audio.currentTime = 0
    setElapsed(0)
    setDuration(activeSoundscape.fallbackDuration)
    audio.load()

    if (autoPlayPendingRef.current) {
      autoPlayPendingRef.current = false
      playActiveAudio()
    }
  }, [activeSoundscape, playActiveAudio])

  const handleSelectSoundscape = (soundscape: Soundscape) => {
    if (isPreparing) return

    if (activeSoundscape?.id === soundscape.id) {
      if (isPlaying) {
        audioRef.current?.pause()
        setIsPlaying(false)
      } else {
        playActiveAudio()
      }
      return
    }

    audioRef.current?.pause()
    autoPlayPendingRef.current = true
    setActiveSoundscape(soundscape)
    setIsPlaying(true)
  }

  const handlePlayPause = () => {
    if (!activeSoundscape) return

    if (isPlaying) {
      audioRef.current?.pause()
      setIsPlaying(false)
    } else {
      playActiveAudio()
    }
  }

  const handleSeek = (delta: number) => {
    const audio = audioRef.current
    if (!activeSoundscape || !audio) return

    const maxDuration = duration || activeSoundscape.fallbackDuration
    const nextTime = Math.max(0, Math.min(maxDuration, audio.currentTime + delta))
    audio.currentTime = nextTime
    setElapsed(nextTime)
  }

  const handleProgressClick = (e: React.MouseEvent<HTMLDivElement>) => {
    const audio = audioRef.current
    if (!activeSoundscape || !audio) return

    const maxDuration = duration || activeSoundscape.fallbackDuration
    const rect = e.currentTarget.getBoundingClientRect()
    const ratio = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width))
    const nextTime = ratio * maxDuration
    audio.currentTime = nextTime
    setElapsed(nextTime)
  }

  const displayDuration = duration || activeSoundscape?.fallbackDuration || 0
  const progress = displayDuration > 0 ? Math.min(100, (elapsed / displayDuration) * 100) : 0

  return (
    <div className="w-full max-w-[300px] overflow-hidden rounded-2xl border border-border/40 bg-card/40">
      <audio
        ref={audioRef}
        src={activeSoundscape?.src}
        preload="metadata"
        loop={isLooping}
      />

      <div className="relative flex h-[120px] items-center justify-center overflow-hidden bg-linear-to-b from-primary/5 to-background">
        {isPreparing ? (
          <div className="text-center">
            <div className="mx-auto mb-2 flex h-12 w-12 items-center justify-center rounded-full border border-primary/30 bg-primary/10">
              <Loader2 className="h-5 w-5 animate-spin text-primary" />
            </div>
            <p className="text-sm font-medium text-foreground">Preparing audio</p>
            <p className="text-xs text-muted-foreground">Checking local files</p>
          </div>
        ) : activeSoundscape && isPlaying ? (
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
        {audioError && (
          <p className="rounded-lg border border-destructive/30 bg-destructive/10 px-2 py-1.5 text-[10px] text-destructive">
            {audioError}
          </p>
        )}

        {activeSoundscape && (
          <div className="space-y-1">
            <div
              className="h-1.5 w-full cursor-pointer overflow-hidden rounded-full bg-border/30"
              onClick={handleProgressClick}
            >
              <div
                className="h-full rounded-full bg-primary transition-all"
                style={{ width: `${progress}%` }}
              />
            </div>
            <div className="flex justify-between text-[10px] text-muted-foreground tabular-nums">
              <span>{formatTime(elapsed)}</span>
              <span>{formatTime(displayDuration)}</span>
            </div>
          </div>
        )}

        {activeSoundscape && (
          <div className="flex items-center justify-center gap-1">
            <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => handleSeek(-10)} title="-10s">
              <SkipBack className="h-3.5 w-3.5" />
            </Button>
            <Button
              size="icon"
              className="h-10 w-10 rounded-full"
              onClick={handlePlayPause}
              disabled={isPreparing}
            >
              {isPlaying ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}
            </Button>
            <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => handleSeek(10)} title="+10s">
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

        {activeSoundscape && (
          <div className="flex items-center gap-2">
            <VolumeX className="h-3 w-3 shrink-0 text-muted-foreground" />
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
              className="h-1 w-full accent-primary"
            />
            <Volume2 className="h-3 w-3 shrink-0 text-muted-foreground" />
          </div>
        )}

        <div className="space-y-1.5">
          {soundscapes.map((soundscape) => {
            const isActive = activeSoundscape?.id === soundscape.id
            return (
              <button
                key={soundscape.id}
                onClick={() => handleSelectSoundscape(soundscape)}
                disabled={isPreparing}
                className={`w-full rounded-lg border p-2.5 text-left transition-colors disabled:cursor-wait disabled:opacity-60 ${
                  isActive
                    ? "border-primary/40 bg-primary/10"
                    : "border-border/40 bg-card/20 hover:border-primary/20"
                }`}
              >
                <div className="flex items-center justify-between gap-2">
                  <div className="min-w-0">
                    <p className={`text-xs font-medium ${isActive ? "text-primary" : "text-foreground"}`}>
                      {soundscape.name}
                    </p>
                    <p className="text-[10px] text-muted-foreground">
                      {soundscape.description}
                    </p>
                  </div>
                  {isActive && isPlaying && (
                    <div className="flex shrink-0 gap-0.5">
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
