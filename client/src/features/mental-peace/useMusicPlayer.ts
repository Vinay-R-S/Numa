"use client"

/**
 * Soundscape player state (NUMA-120 P4, PLAN 21.2).
 *
 * Everything `MusicPlayer` held inline: the audio-library prepare call, the
 * selected soundscape, transport state, volume/loop/mute and seeking. The
 * component keeps the `<audio>` element and passes its ref in.
 */
import { useCallback, useEffect, useRef, useState } from "react"
import type { RefObject } from "react"
import { AUDIO_PARTIAL_ERROR, AUDIO_PREPARE_ERROR, ensureAudioLibrary } from "./mentalPeace.api"
import { DEFAULT_PLAYER_VOLUME } from "./mentalPeace.constants"
import type { Soundscape } from "./mentalPeace.types"

export interface UseMusicPlayerReturn {
  audioRef: RefObject<HTMLAudioElement | null>
  activeSoundscape: Soundscape | null
  isPlaying: boolean
  isMuted: boolean
  isLooping: boolean
  isPreparing: boolean
  volume: number
  elapsed: number
  displayDuration: number
  progress: number
  audioError: string | null
  selectSoundscape: (soundscape: Soundscape) => void
  togglePlay: () => void
  toggleLoop: () => void
  toggleMute: () => void
  changeVolume: (value: number) => void
  seekBy: (delta: number) => void
  seekToRatio: (ratio: number) => void
}

export function useMusicPlayer(): UseMusicPlayerReturn {
  const [activeSoundscape, setActiveSoundscape] = useState<Soundscape | null>(null)
  const [isPlaying, setIsPlaying] = useState(false)
  const [isMuted, setIsMuted] = useState(false)
  const [isLooping, setIsLooping] = useState(true)
  const [volume, setVolume] = useState(DEFAULT_PLAYER_VOLUME)
  const [elapsed, setElapsed] = useState(0)
  const [duration, setDuration] = useState(0)
  const [isPreparing, setIsPreparing] = useState(true)
  const [audioError, setAudioError] = useState<string | null>(null)

  const audioRef = useRef<HTMLAudioElement | null>(null)
  const autoPlayPendingRef = useRef(false)

  useEffect(() => {
    let cancelled = false

    async function prepareLibrary() {
      setIsPreparing(true)
      setAudioError(null)
      try {
        await ensureAudioLibrary()
      } catch (err) {
        // Only the partial-download message is meant for this banner: an
        // ApiError carries the proxy's detail (internal backend address and
        // all) and a schema mismatch carries a ZodError dump.
        const partial = err instanceof Error && err.message === AUDIO_PARTIAL_ERROR
        if (!cancelled) setAudioError(partial ? AUDIO_PARTIAL_ERROR : AUDIO_PREPARE_ERROR)
      } finally {
        if (!cancelled) setIsPreparing(false)
      }
    }

    prepareLibrary()

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

  const fallbackDuration = activeSoundscape?.fallbackDuration

  useEffect(() => {
    const audio = audioRef.current
    if (!audio) return

    const handleTimeUpdate = () => setElapsed(audio.currentTime)
    const handleLoadedMetadata = () => {
      setDuration(Number.isFinite(audio.duration) ? audio.duration : fallbackDuration || 0)
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
  }, [fallbackDuration])

  const playActive = useCallback(async () => {
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
      playActive()
    }
  }, [activeSoundscape, playActive])

  const selectSoundscape = useCallback(
    (soundscape: Soundscape) => {
      if (isPreparing) return

      if (activeSoundscape?.id === soundscape.id) {
        if (isPlaying) {
          audioRef.current?.pause()
          setIsPlaying(false)
          return
        }

        playActive()
        return
      }

      audioRef.current?.pause()
      autoPlayPendingRef.current = true
      setActiveSoundscape(soundscape)
      setIsPlaying(true)
    },
    [activeSoundscape, isPlaying, isPreparing, playActive]
  )

  const togglePlay = useCallback(() => {
    if (!activeSoundscape) return

    if (isPlaying) {
      audioRef.current?.pause()
      setIsPlaying(false)
      return
    }

    playActive()
  }, [activeSoundscape, isPlaying, playActive])

  const seekTo = useCallback(
    (nextTime: number) => {
      const audio = audioRef.current
      if (!activeSoundscape || !audio) return

      const maxDuration = duration || activeSoundscape.fallbackDuration
      const clamped = Math.max(0, Math.min(maxDuration, nextTime))
      audio.currentTime = clamped
      setElapsed(clamped)
    },
    [activeSoundscape, duration]
  )

  const seekBy = useCallback(
    (delta: number) => seekTo((audioRef.current?.currentTime ?? 0) + delta),
    [seekTo]
  )

  const seekToRatio = useCallback(
    (ratio: number) => {
      if (!activeSoundscape) return
      seekTo(Math.max(0, Math.min(1, ratio)) * (duration || activeSoundscape.fallbackDuration))
    },
    [activeSoundscape, duration, seekTo]
  )

  const changeVolume = useCallback((value: number) => {
    setVolume(value)
    if (value > 0) setIsMuted((muted) => (muted ? false : muted))
  }, [])

  const toggleLoop = useCallback(() => setIsLooping((looping) => !looping), [])
  const toggleMute = useCallback(() => setIsMuted((muted) => !muted), [])

  const displayDuration = duration || activeSoundscape?.fallbackDuration || 0
  const progress = displayDuration > 0 ? Math.min(100, (elapsed / displayDuration) * 100) : 0

  return {
    audioRef,
    activeSoundscape,
    isPlaying,
    isMuted,
    isLooping,
    isPreparing,
    volume,
    elapsed,
    displayDuration,
    progress,
    audioError,
    selectSoundscape,
    togglePlay,
    toggleLoop,
    toggleMute,
    changeVolume,
    seekBy,
    seekToRatio,
  }
}
