"use client"

import { useMusicPlayer } from "../useMusicPlayer"
import { PlayerControls } from "./PlayerControls"
import { SoundscapeList } from "./SoundscapeList"
import { SoundscapeStage } from "./SoundscapeStage"
import { TrackProgress } from "./TrackProgress"
import { VolumeSlider } from "./VolumeSlider"

export function MusicPlayer() {
  const {
    audioRef,
    soundscapes,
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
    retryPrepare,
    selectSoundscape,
    togglePlay,
    toggleLoop,
    toggleMute,
    changeVolume,
    seekBy,
    seekToRatio,
  } = useMusicPlayer()

  return (
    <div className="w-full max-w-[300px] overflow-hidden rounded-2xl border border-border/40 bg-card/40">
      <audio
        ref={audioRef}
        src={activeSoundscape?.src}
        preload="metadata"
        loop={isLooping}
      />

      <SoundscapeStage
        soundscape={activeSoundscape}
        isPlaying={isPlaying}
        isPreparing={isPreparing}
      />

      <div className="p-3 sm:p-4 space-y-3">
        {audioError && (
          <p className="rounded-lg border border-destructive/30 bg-destructive/10 px-2 py-1.5 text-[10px] text-destructive">
            {audioError}
          </p>
        )}

        {activeSoundscape && (
          <>
            <TrackProgress
              elapsed={elapsed}
              duration={displayDuration}
              progress={progress}
              onSeekToRatio={seekToRatio}
            />

            <PlayerControls
              isPlaying={isPlaying}
              isMuted={isMuted}
              isLooping={isLooping}
              isPreparing={isPreparing}
              onSeekBy={seekBy}
              onTogglePlay={togglePlay}
              onToggleLoop={toggleLoop}
              onToggleMute={toggleMute}
            />

            <VolumeSlider
              volume={volume}
              isMuted={isMuted}
              onChange={changeVolume}
            />
          </>
        )}

        <SoundscapeList
          soundscapes={soundscapes}
          activeId={activeSoundscape?.id ?? null}
          isPlaying={isPlaying}
          isPreparing={isPreparing}
          onSelect={selectSoundscape}
          onRetry={retryPrepare}
        />
      </div>
    </div>
  )
}
