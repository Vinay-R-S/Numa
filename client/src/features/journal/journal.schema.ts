/**
 * Journal validation schemas (NUMA-112 P4, PLAN 22.2 / 22.3).
 *
 * Mirrors the backend Pydantic bounds in `server/src/journal/schemas.py`.
 * Response schemas run in `journal.api.ts` via the shared `http` `schema`
 * option so runtime data is type-safe and API contract drift fails loudly.
 * Date/timestamp fields are kept as plain strings so `date`/`datetime`
 * serialization is tolerated while response structure is still validated.
 * Input schemas mirror JournalEntryCreate/Update for the form layer.
 */
import { z } from "@/lib/validation"

export const moodSchema = z.enum(["great", "good", "okay", "bad", "terrible"])

export const journalEntrySchema = z.object({
  id: z.string(),
  user_id: z.string(),
  title: z.string(),
  content: z.string(),
  mood: moodSchema.nullable(),
  entry_date: z.string(),
  tags: z.array(z.string()).default([]),
  ai_summary: z.string().nullable(),
  created_at: z.string(),
  updated_at: z.string(),
})

export const journalListResponseSchema = z.object({
  entries: z.array(journalEntrySchema),
  total: z.number(),
})

export const journalSummaryResponseSchema = z.object({
  summary: z.string(),
  entry_date: z.string(),
})

// Input: mirrors backend JournalEntryCreate / JournalEntryUpdate for the form layer.
export const journalCreateSchema = z.object({
  title: z.string().trim().default(""),
  content: z.string().default(""),
  mood: moodSchema.nullish(),
  entry_date: z.string().optional(),
  tags: z.array(z.string()).default([]),
})

export const journalUpdateSchema = z.object({
  title: z.string().trim().optional(),
  content: z.string().optional(),
  mood: moodSchema.nullish(),
  tags: z.array(z.string()).optional(),
})

export type JournalCreateInput = z.infer<typeof journalCreateSchema>
export type JournalUpdateInput = z.infer<typeof journalUpdateSchema>
