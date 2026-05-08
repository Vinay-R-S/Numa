const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

function getAuthHeaders(): Record<string, string> {
  if (typeof window === "undefined") return {}
  const token = localStorage.getItem("numa_token")
  if (!token) return {}
  return { Authorization: `Bearer ${token}` }
}

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

export async function listJournalEntries(
  limit = 30,
  offset = 0
): Promise<JournalListResponse> {
  const res = await fetch(
    `${API_BASE}/api/journal?limit=${limit}&offset=${offset}`,
    { headers: { ...getAuthHeaders(), "Content-Type": "application/json" } }
  )
  if (!res.ok) throw new Error(`Failed to fetch journal entries: ${res.status}`)
  return res.json()
}

export async function getJournalEntry(entryDate: string): Promise<JournalEntry> {
  const res = await fetch(`${API_BASE}/api/journal/${entryDate}`, {
    headers: { ...getAuthHeaders(), "Content-Type": "application/json" },
  })
  if (!res.ok) {
    if (res.status === 404) throw new Error("NOT_FOUND")
    throw new Error(`Failed to fetch entry: ${res.status}`)
  }
  return res.json()
}

export async function createJournalEntry(body: {
  title: string
  content: string
  mood?: string | null
  entry_date?: string
  tags?: string[]
}): Promise<JournalEntry> {
  const res = await fetch(`${API_BASE}/api/journal`, {
    method: "POST",
    headers: { ...getAuthHeaders(), "Content-Type": "application/json" },
    body: JSON.stringify(body),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || `Failed to create entry: ${res.status}`)
  }
  return res.json()
}

export async function updateJournalEntry(
  entryDate: string,
  body: {
    title?: string
    content?: string
    mood?: string | null
    tags?: string[]
  }
): Promise<JournalEntry> {
  const res = await fetch(`${API_BASE}/api/journal/${entryDate}`, {
    method: "PUT",
    headers: { ...getAuthHeaders(), "Content-Type": "application/json" },
    body: JSON.stringify(body),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || `Failed to update entry: ${res.status}`)
  }
  return res.json()
}

export async function deleteJournalEntry(entryDate: string): Promise<void> {
  const res = await fetch(`${API_BASE}/api/journal/${entryDate}`, {
    method: "DELETE",
    headers: getAuthHeaders(),
  })
  if (!res.ok) throw new Error(`Failed to delete entry: ${res.status}`)
}

export async function autoGenerateJournal(): Promise<JournalEntry> {
  const res = await fetch(`${API_BASE}/api/journal/auto-generate`, {
    method: "POST",
    headers: { ...getAuthHeaders(), "Content-Type": "application/json" },
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || `Failed to auto-generate journal: ${res.status}`)
  }
  return res.json()
}

export async function generateDaySummary(
  entryDate?: string
): Promise<JournalSummaryResponse> {
  const res = await fetch(`${API_BASE}/api/journal/summarize`, {
    method: "POST",
    headers: { ...getAuthHeaders(), "Content-Type": "application/json" },
    body: JSON.stringify({ entry_date: entryDate || null }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || `Failed to generate summary: ${res.status}`)
  }
  return res.json()
}
