"use client"

import Image from "next/image"
import { CheckCircle2 } from "lucide-react"
import { yogaPoses } from "../data"
import { MeditationTimer } from "./MeditationTimer"
import { MusicPlayer } from "./MusicPlayer"

const MEDITATION_POSTURE_ID = "thunderbolt"
const VISIBLE_INSTRUCTIONS = 4

export function MeditationSession() {
  const posture = yogaPoses[MEDITATION_POSTURE_ID]

  return (
    <div className="h-full overflow-hidden bg-background px-2 py-4 sm:px-4">
      <div className="mx-auto flex h-full max-w-6xl flex-col gap-4">
        <div className="shrink-0 text-center">
          <h2 className="text-2xl font-bold text-foreground">Meditation</h2>
          <p className="mt-2 text-sm text-muted-foreground">
            Choose music, set a timer, and settle into one steady posture.
          </p>
        </div>

        <div className="grid min-h-0 flex-1 grid-cols-1 gap-4 overflow-hidden lg:grid-cols-[minmax(0,1fr)_320px_320px]">
          <section className="overflow-hidden rounded-2xl border border-border/40 bg-card/40 p-4 sm:p-5">
            <div className="overflow-hidden rounded-2xl border border-border/40 bg-background/40">
              <Image
                src={posture.imageUrl}
                alt={posture.englishName}
                width={900}
                height={520}
                unoptimized
                className="h-52 w-full object-cover sm:h-60"
              />
            </div>
            <div className="mt-5">
              <h3 className="text-xl font-bold text-foreground">{posture.englishName}</h3>
              <p className="mt-1 text-sm italic text-muted-foreground">
                {posture.sanskritName} ({posture.pronunciation})
              </p>
              <div className="mt-4 space-y-2">
                {posture.instructions.slice(0, VISIBLE_INSTRUCTIONS).map((instruction) => (
                  <div key={instruction} className="flex gap-2 text-sm text-muted-foreground">
                    <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-foreground" />
                    <span>{instruction}</span>
                  </div>
                ))}
              </div>
            </div>
          </section>

          <div className="flex justify-center">
            <MusicPlayer />
          </div>

          <div className="flex justify-center">
            <MeditationTimer />
          </div>
        </div>
      </div>
    </div>
  )
}
