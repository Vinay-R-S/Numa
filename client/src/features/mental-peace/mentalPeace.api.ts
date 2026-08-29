/**
 * Mental peace API (NUMA-120 P4, PLAN 17.5 / 21.2 / 22.2).
 *
 * Replaces the two raw `fetch("/api/audio-library/ensure")` calls the page and
 * the music player each ran inline. The soundscape files themselves stay plain
 * `<audio src>` URLs: they are streamed by the browser, not fetched as JSON.
 *
 * Behavior carried over: a 200 answering `{ ok: false }` means some file could
 * not be downloaded, which the player surfaces as an error, so the check stays
 * here rather than in the hook (PLAN features/README migration notes). It
 * throws an `AudioLibraryPartialError` (NUMA-124) so the caller keeps the
 * catalog it came with: the player drives its track list off these items and a
 * failed download still names every track.
 */
import { expectBody, http } from "@/lib/http"
import { audioLibraryEnsureSchema } from "./mentalPeace.schema"
import type { AudioLibraryEnsureResult } from "./mentalPeace.types"

export const AUDIO_PREPARE_ERROR = "Unable to prepare local audio"
export const AUDIO_PARTIAL_ERROR = "Some audio files could not be downloaded"

export class AudioLibraryPartialError extends Error {
  readonly result: AudioLibraryEnsureResult

  constructor(result: AudioLibraryEnsureResult) {
    super(AUDIO_PARTIAL_ERROR)
    this.name = "AudioLibraryPartialError"
    this.result = result
  }
}

export async function ensureAudioLibrary(): Promise<AudioLibraryEnsureResult> {
  const result = await expectBody(
    http.post<AudioLibraryEnsureResult>("/audio-library/ensure", undefined, {
      schema: audioLibraryEnsureSchema,
      errorMessage: AUDIO_PREPARE_ERROR,
    }),
    AUDIO_PREPARE_ERROR
  )

  if (!result.ok) throw new AudioLibraryPartialError(result)

  return result
}
