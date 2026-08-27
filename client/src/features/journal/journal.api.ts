/**
 * Journal API (NUMA-112 P4, PLAN 21.2 / 22.2).
 *
 * Typed fetchers built on the shared `http` client. Curated fallback error text
 * is kept per endpoint (backend `{ detail }` still wins) and responses are
 * validated with the feature's zod schemas. The old `NOT_FOUND` sentinel string
 * on a 404 is gone: callers inspect the typed `ApiError` instead, so the
 * backend detail ("No journal entry for <date>") reaches the UI.
 *
 * Every endpoint but the delete answers with JSON. `http` resolves a body-less
 * or non-JSON 2xx to `undefined` (a proxy that drops the content-type header is
 * enough), which would put `undefined` into React state and crash the next
 * render, so `expectBody` turns that into the endpoint's error.
 */
import { expectBody, http } from "@/lib/http"
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
  const message = "Failed to fetch journal entries"
  return expectBody(
    http.get("/journal", {
      query: { limit, offset },
      schema: journalListResponseSchema,
      errorMessage: message,
    }),
    message
  )
}

export function getJournalEntry(entryDate: string): Promise<JournalEntry> {
  const message = "Failed to fetch entry"
  return expectBody(
    http.get(`/journal/${entryDate}`, {
      schema: journalEntrySchema,
      errorMessage: message,
    }),
    message
  )
}

export function createJournalEntry(body: {
  title: string
  content: string
  mood?: string | null
  entry_date?: string
  tags?: string[]
}): Promise<JournalEntry> {
  const message = "Failed to create entry"
  return expectBody(
    http.post("/journal", body, {
      schema: journalEntrySchema,
      errorMessage: message,
    }),
    message
  )
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
  const message = "Failed to update entry"
  return expectBody(
    http.put(`/journal/${entryDate}`, body, {
      schema: journalEntrySchema,
      errorMessage: message,
    }),
    message
  )
}

export function deleteJournalEntry(entryDate: string): Promise<void> {
  return http.del(`/journal/${entryDate}`, { errorMessage: "Failed to delete entry" })
}

export function autoGenerateJournal(): Promise<JournalEntry> {
  const message = "Failed to auto-generate journal"
  return expectBody(
    http.post("/journal/auto-generate", undefined, {
      schema: journalEntrySchema,
      errorMessage: message,
    }),
    message
  )
}

export function generateDaySummary(entryDate?: string): Promise<JournalSummaryResponse> {
  const message = "Failed to generate summary"
  return expectBody(
    http.post("/journal/summarize", { entry_date: entryDate || null }, {
      schema: journalSummaryResponseSchema,
      errorMessage: message,
    }),
    message
  )
}
