/**
 * Mental peace validation schemas (NUMA-120 P4, PLAN 22.2 / 22.3).
 *
 * Mirrors the `/audio-library/ensure` payload, which NUMA-124 gave a real
 * `response_model` (`server/src/audio_library/schemas.py`). Items stay
 * `looseObject`: only the fields the player reads are declared here, and the
 * licensing metadata it ignores passes through untouched.
 */
import { z } from "@/lib/validation"
import type { AudioLibraryEnsureResult, AudioLibraryFailure, AudioLibraryItem } from "./mentalPeace.types"

export const audioLibraryItemSchema: z.ZodType<AudioLibraryItem> = z.looseObject({
  id: z.string(),
  kind: z.string(),
  label: z.string(),
  description: z.string(),
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
