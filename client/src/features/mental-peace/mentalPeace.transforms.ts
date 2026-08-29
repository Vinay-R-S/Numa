/**
 * Mental peace API-DTO -> view-model mappers (NUMA-124, PLAN 10 / 21.2).
 *
 * `SOUNDSCAPES` used to repeat the id, label, description, filename and
 * duration of `server/src/audio_library/constants.AUDIO_LIBRARY`. The player
 * builds the list from the `/audio-library/ensure` items instead, so the server
 * catalog is the only place a track is described.
 *
 * `url` arrives as the backend path (`/audio/<file>`); the `/api` prefix is the
 * Next proxy hop, the same one `lib/http` adds to its own requests.
 */
import type { AudioLibraryItem, Soundscape } from "./mentalPeace.types"

export function toSoundscape(item: AudioLibraryItem): Soundscape {
  return {
    id: item.id,
    name: item.label,
    description: item.description,
    src: `/api${item.url}`,
    fallbackDuration: item.duration_seconds,
  }
}

export function toSoundscapes(items: AudioLibraryItem[]): Soundscape[] {
  return items.map(toSoundscape)
}
