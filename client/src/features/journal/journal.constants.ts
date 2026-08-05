import type { MoodKey } from "./journal.types"

export const MOODS: ReadonlyArray<{ key: MoodKey; emoji: string; label: string }> = [
  { key: "great", emoji: "😊", label: "Great" },
  { key: "good", emoji: "🙂", label: "Good" },
  { key: "okay", emoji: "😐", label: "Okay" },
  { key: "bad", emoji: "😔", label: "Bad" },
  { key: "terrible", emoji: "😢", label: "Terrible" },
]
