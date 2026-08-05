/**
 * Journal API (NUMA-112 P4, PLAN 21.2 / 22.2).
 *
 * Typed fetchers built on the shared `http` client. Curated fallback error text
 * is kept per endpoint (backend `{ detail }` still wins) and responses are
 * validated with the feature's zod schemas. The old `NOT_FOUND` sentinel string
 * on a 404 is gone: callers inspect the typed `ApiError` instead, so the
 * backend detail ("No journal entry for <date>") reaches the UI.
 */
import { http } from "@/lib/http"
import type {
  JournalEntry,
  JournalListResponse,
  JournalSummaryResponse,
} from "./journal.types"
import {
  journalEntrySchema,
  journalListResponseSchema,
  journalSummaryResponseSchema,
} from "./journal.schema"

export function listJournalEntries(limit = 30, offset = 0): Promise<JournalListResponse> {
  return http.get("/journal", {
    query: { limit, offset },
    schema: journalListResponseSchema,
    errorMessage: "Failed to fetch journal entries",
  })
}

export function getJournalEntry(entryDate: string): Promise<JournalEntry> {
  return http.get(`/journal/${entryDate}`, {
    schema: journalEntrySchema,
    errorMessage: "Failed to fetch entry",
  })
}

export function createJournalEntry(body: {
  title: string
  content: string
  mood?: string | null
  entry_date?: string
  tags?: string[]
}): Promise<JournalEntry> {
  return http.post("/journal", body, {
    schema: journalEntrySchema,
    errorMessage: "Failed to create entry",
  })
}

export function updateJournalEntry(
  entryDate: string,
  body: {
    title?: string
    content?: string
    mood?: string | null
    tags?: string[]
  }
): Promise<JournalEntry> {
  return http.put(`/journal/${entryDate}`, body, {
    schema: journalEntrySchema,
    errorMessage: "Failed to update entry",
  })
}

export function deleteJournalEntry(entryDate: string): Promise<void> {
  return http.del(`/journal/${entryDate}`, { errorMessage: "Failed to delete entry" })
}

export function autoGenerateJournal(): Promise<JournalEntry> {
  return http.post("/journal/auto-generate", undefined, {
    schema: journalEntrySchema,
    errorMessage: "Failed to auto-generate journal",
  })
}

export function generateDaySummary(entryDate?: string): Promise<JournalSummaryResponse> {
  return http.post("/journal/summarize", { entry_date: entryDate || null }, {
    schema: journalSummaryResponseSchema,
    errorMessage: "Failed to generate summary",
  })
}
