export type MoodKey = "great" | "good" | "okay" | "bad" | "terrible"

export interface JournalEntry {
  id: string
  user_id: string
  title: string
  content: string
  mood: string | null
  entry_date: string
  tags: string[]
  ai_summary: string | null
  created_at: string
  updated_at: string
}

export interface JournalListResponse {
  entries: JournalEntry[]
  total: number
}

export interface JournalSummaryResponse {
  summary: string
  entry_date: string
}
