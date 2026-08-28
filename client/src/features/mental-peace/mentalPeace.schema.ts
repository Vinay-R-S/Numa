/**
 * Mental peace validation schemas (NUMA-120 P4, PLAN 22.2 / 22.3).
 *
 * Mirrors the `/audio-library/ensure` payload built in
 * `server/src/audio_library/router.py`. That router has no `response_model`, so
 * items are `looseObject`: only the fields the client reads are required and
 * the licensing metadata passes through untouched.
 */
import { z } from "@/lib/validation"
import type { AudioLibraryEnsureResult, AudioLibraryFailure, AudioLibraryItem } from "./mentalPeace.types"

export const audioLibraryItemSchema: z.ZodType<AudioLibraryItem> = z.looseObject({
  id: z.string(),
  kind: z.string(),
  label: z.string(),
  filename: z.string(),
  duration_seconds: z.number(),
  url: z.string(),
  ready: z.boolean(),
})

export const audioLibraryFailureSchema: z.ZodType<AudioLibraryFailure> = z.looseObject({
  id: z.string(),
  detail: z.string(),
})

export const audioLibraryEnsureSchema: z.ZodType<AudioLibraryEnsureResult> = z.looseObject({
  ok: z.boolean(),
  downloaded: z.array(z.string()),
  failed: z.array(audioLibraryFailureSchema),
  items: z.array(audioLibraryItemSchema),
})
