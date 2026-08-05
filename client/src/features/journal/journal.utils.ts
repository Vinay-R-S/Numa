import { MOODS } from "./journal.constants"

export function moodEmoji(mood: string | null): string {
  return MOODS.find((m) => m.key === mood)?.emoji ?? ""
}

export function todayDateStr(): string {
  return new Date().toISOString().slice(0, 10)
}

export function formatSidebarDate(dateStr: string): string {
  const d = new Date(dateStr + "T00:00:00")
  return d.toLocaleDateString("en-US", { weekday: "short", month: "short", day: "numeric" })
}

export function formatEntryDate(dateStr: string): string {
  const d = new Date(dateStr + "T00:00:00")
  return d.toLocaleDateString("en-US", {
    weekday: "long",
    year: "numeric",
    month: "long",
    day: "numeric",
  })
}

export function formatTime(isoStr: string): string {
  const d = new Date(isoStr)
  return d.toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" })
}
