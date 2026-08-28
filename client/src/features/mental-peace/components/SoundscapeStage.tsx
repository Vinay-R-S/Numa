"use client"

import { Loader2, Pause, Volume2 } from "lucide-react"
import type { ReactNode } from "react"
import type { Soundscape } from "../mentalPeace.types"

interface SoundscapeStageProps {
  soundscape: Soundscape | null
  isPlaying: boolean
  isPreparing: boolean
}

interface StageMessageProps {
  icon: ReactNode
  iconClassName: string
  title: string
  subtitle?: string
  titleClassName?: string
}

function StageMessage({ icon, iconClassName, title, subtitle, titleClassName }: StageMessageProps) {
  return (
    <div className="text-center">
      <div className={iconClassName}>{icon}</div>
      <p className={titleClassName ?? "text-sm font-medium text-foreground"}>{title}</p>
      {subtitle && <p className="text-xs text-muted-foreground">{subtitle}</p>}
    </div>
  )
}

const ACTIVE_ICON =
  "mx-auto mb-2 flex h-12 w-12 items-center justify-center rounded-full border border-primary/30 bg-primary/10"
const IDLE_ICON =
  "mx-auto mb-2 flex h-12 w-12 items-center justify-center rounded-full border border-border/40 bg-card/40"

export function SoundscapeStage({ soundscape, isPlaying, isPreparing }: SoundscapeStageProps) {
  if (isPreparing) {
    return (
      <StageShell>
        <StageMessage
          icon={<Loader2 className="h-5 w-5 animate-spin text-primary" />}
          iconClassName={ACTIVE_ICON}
          title="Preparing audio"
          subtitle="Checking local files"
        />
      </StageShell>
    )
  }

  if (!soundscape) {
    return (
      <StageShell>
        <StageMessage
          icon={<Volume2 className="h-6 w-6 text-muted-foreground" />}
          iconClassName={IDLE_ICON}
          title="Select a soundscape"
          titleClassName="text-sm text-muted-foreground"
        />
      </StageShell>
    )
  }

  if (!isPlaying) {
    return (
      <StageShell>
        <StageMessage
          icon={<Pause className="h-6 w-6 text-muted-foreground" />}
          iconClassName={IDLE_ICON}
          title={soundscape.name}
          subtitle="Paused"
        />
      </StageShell>
    )
  }

  return (
    <StageShell>
      <StageMessage
        icon={<Volume2 className="h-6 w-6 text-primary" />}
        iconClassName={ACTIVE_ICON + " animate-pulse"}
        title={soundscape.name}
        subtitle={soundscape.description}
      />
    </StageShell>
  )
}

function StageShell({ children }: { children: ReactNode }) {
  return (
    <div className="relative flex h-[120px] items-center justify-center overflow-hidden bg-linear-to-b from-primary/5 to-background">
      {children}
    </div>
  )
}
