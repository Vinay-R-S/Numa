"use client"

import { Moon } from "lucide-react"

import { SLEEP_GOAL_HOURS, SLEEP_STAGE_META, SLEEP_STAGE_ORDER } from "../health.constants"
import type { HealthSnapshot, SleepStage } from "../health.types"
import {
  formatSleepDuration,
  formatSleepTime,
  normalizeSleepSegments,
  parseSleepTimestamp,
} from "../health.utils"

const STATUS_BADGE: Record<string, string> = {
  Review: "border-amber-500/20 bg-amber-500/10 text-amber-300",
  "On target": "border-emerald-500/20 bg-emerald-500/10 text-emerald-400",
  Close: "border-yellow-500/20 bg-yellow-500/10 text-yellow-400",
  Low: "border-orange-500/20 bg-orange-500/10 text-orange-400",
}

function sleepStatusLabel(longWindow: boolean, quality: number): string {
  if (longWindow) return "Review"
  if (quality >= 85) return "On target"
  if (quality >= 65) return "Close"
  return "Low"
}

function EmptySleepCard() {
  return (
    <div className="flex flex-col items-center justify-center gap-3 rounded-2xl border border-border/40 bg-card/40 p-6 min-h-[200px]">
      <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-indigo-500/10">
        <Moon className="h-6 w-6 text-indigo-400/50" />
      </div>
      <p className="text-sm font-medium text-muted-foreground">No sleep data</p>
      <p className="text-xs text-muted-foreground/60 text-center max-w-[200px]">
        Sleep tracking must be enabled in Google Fit or a connected wearable.
      </p>
    </div>
  )
}

export function SleepCard({ snapshot }: { snapshot: HealthSnapshot | null }) {
  const sleep = snapshot?.sleep_hours

  if (!sleep || sleep <= 0) return <EmptySleepCard />

  const goal = SLEEP_GOAL_HOURS
  const normalizedSegments = normalizeSleepSegments(snapshot?.sleep_segments)
  const segmentHours = normalizedSegments.reduce((sum, segment) => sum + segment.hours, 0)
  const displaySleep = segmentHours > 0 ? segmentHours : sleep
  const rawSleepDiffers = segmentHours > 0 && Math.abs(sleep - segmentHours) >= 0.25
  const quality = Math.min(100, Math.round((displaySleep / goal) * 100))
  const sleepStart = normalizedSegments[0]?.startMs ?? parseSleepTimestamp(snapshot?.sleep_start_at)
  const sleepEnd =
    normalizedSegments[normalizedSegments.length - 1]?.endMs ??
    parseSleepTimestamp(snapshot?.sleep_end_at)
  const timelineStart = sleepStart ?? 0
  const timelineEnd = sleepEnd ?? timelineStart + displaySleep * 60 * 60 * 1000
  const timelineSpan = Math.max(timelineEnd - timelineStart, displaySleep * 60 * 60 * 1000, 1)
  const timelineSegments =
    normalizedSegments.length > 0
      ? normalizedSegments
      : [
          {
            startMs: timelineStart,
            endMs: timelineEnd,
            stage: "generic" as SleepStage,
            hours: displaySleep,
          },
        ]
  const longWindow = displaySleep > 12
  const stageTotals = timelineSegments.reduce<Record<SleepStage, number>>(
    (acc, segment) => {
      acc[segment.stage] += segment.hours
      return acc
    },
    { generic: 0, light: 0, deep: 0, rem: 0 }
  )
  const stageList = SLEEP_STAGE_ORDER.map((stage) => ({
    stage,
    hours: stageTotals[stage],
    ...SLEEP_STAGE_META[stage],
  })).filter((stage) => stage.hours > 0)
  const sleepStatus = sleepStatusLabel(longWindow, quality)

  return (
    <div className="rounded-2xl border border-border/40 bg-card/40 p-5 sm:p-6">
      <div className="mb-5 flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-indigo-500/10 ring-1 ring-indigo-500/20">
            <Moon className="h-5 w-5 text-indigo-400" />
          </div>
          <div>
            <h3 className="text-base font-bold text-foreground">Sleep Analysis</h3>
            <p className="text-xs text-muted-foreground">Last night</p>
          </div>
        </div>
        <span className={`rounded-full border px-2.5 py-0.5 text-xs font-bold ${STATUS_BADGE[sleepStatus]}`}>
          {sleepStatus}
        </span>
      </div>

      <div className="mb-5 grid gap-2 sm:grid-cols-3">
        <div className="rounded-xl border border-border/30 bg-background/30 px-3 py-2.5">
          <p className="text-[10px] font-medium uppercase text-muted-foreground/70">Duration</p>
          <p className="text-2xl font-black text-indigo-300 tabular-nums">{formatSleepDuration(displaySleep)}</p>
          {rawSleepDiffers && (
            <p className="mt-1 text-[10px] text-amber-300">Adjusted from {formatSleepDuration(sleep)}</p>
          )}
        </div>
        <div className="rounded-xl border border-border/30 bg-background/30 px-3 py-2.5">
          <p className="text-[10px] font-medium uppercase text-muted-foreground/70">Window</p>
          <p className="text-lg font-bold text-foreground tabular-nums">
            {formatSleepTime(sleepStart)} to {formatSleepTime(sleepEnd)}
          </p>
          <p className="mt-1 text-[10px] text-muted-foreground">{formatSleepDuration(goal)} goal</p>
        </div>
        <div className="rounded-xl border border-border/30 bg-background/30 px-3 py-2.5">
          <p className="text-[10px] font-medium uppercase text-muted-foreground/70">Goal</p>
          <p className="text-2xl font-black text-foreground tabular-nums">{quality}%</p>
          <p className="mt-1 text-[10px] text-muted-foreground">
            {formatSleepDuration(Math.max(goal - displaySleep, 0))} remaining
          </p>
        </div>
      </div>

      <div className="space-y-2">
        <div className="flex items-center justify-between text-[10px] font-medium uppercase text-muted-foreground/70">
          <span>Sleep timeline</span>
          <span>{formatSleepDuration(displaySleep)}</span>
        </div>
        <div className="relative h-12 overflow-hidden rounded-xl border border-border/30 bg-background/40">
          <div className="absolute inset-x-0 bottom-0 h-px bg-border/40" />
          {timelineSegments.map((segment) => {
            const left = ((segment.startMs - timelineStart) / timelineSpan) * 100
            const width = ((segment.endMs - segment.startMs) / timelineSpan) * 100
            return (
              <div
                key={`${segment.stage}-${segment.startMs}`}
                className={`absolute top-2 h-8 min-w-[3px] rounded-md ${SLEEP_STAGE_META[segment.stage].fill}`}
                style={{ left: `${Math.max(0, left)}%`, width: `${Math.max(1, width)}%` }}
                title={`${SLEEP_STAGE_META[segment.stage].label}: ${formatSleepDuration(segment.hours)}`}
              />
            )
          })}
        </div>
        <div className="flex items-center justify-between text-[11px] text-muted-foreground">
          <span>{formatSleepTime(sleepStart)}</span>
          <span>{formatSleepTime(sleepEnd)}</span>
        </div>
      </div>

      {stageList.length > 0 && (
        <div className="mt-4 grid grid-cols-2 gap-2 sm:grid-cols-4">
          {stageList.map((stage) => (
            <div key={stage.stage} className="rounded-lg border border-border/30 bg-background/30 p-2.5">
              <div className="mb-1 flex items-center gap-1.5">
                <div className={`h-2 w-2 rounded-full ${stage.dot}`} />
                <span className="text-[10px] text-muted-foreground">{stage.label}</span>
              </div>
              <p className="text-sm font-bold text-foreground tabular-nums">{formatSleepDuration(stage.hours)}</p>
            </div>
          ))}
        </div>
      )}

      {(longWindow || rawSleepDiffers) && (
        <div className="mt-4 rounded-lg border border-amber-500/20 bg-amber-500/10 px-3 py-2 text-xs text-amber-200">
          {longWindow
            ? "Google Fit returned a long sleep window. Re-sync after the watch app finishes uploading if this looks wrong."
            : "Overlapping synced sleep segments were collapsed into a single timeline."}
        </div>
      )}
    </div>
  )
}
