"""Audio library catalog and paths (NUMA-124, PLAN 2.1 / 10 / 21.1).

The catalog `router.py` carried inline as a list of loosely typed dicts. It is
the single source of truth for the mental-peace soundscape list: the client used
to repeat every id, label, filename and duration in
`features/mental-peace/mentalPeace.constants.ts` and now reads them from
`/audio-library/ensure` (PLAN 10).

`description` is the one field the client owned that the server did not; it
moved here with the rest so the two catalogs cannot drift.
"""
from __future__ import annotations

from pathlib import Path

from .schemas import AudioLibraryEntry

SERVER_ROOT = Path(__file__).resolve().parents[2]
AUDIO_ROOT = SERVER_ROOT / "audio"

# A well-formed .ogg from these sources is far larger than this; anything under
# it is a truncated download or an error page saved with an audio extension.
MIN_AUDIO_BYTES = 100_000

AUDIO_LIBRARY: list[AudioLibraryEntry] = [
    AudioLibraryEntry(
        id="rain-thunder-birds",
        kind="soundscape",
        label="Rain and Birds",
        description="Rainfall with soft thunder and birds",
        filename="rain-thunder-birds.ogg",
        duration_seconds=134,
        source_url="https://upload.wikimedia.org/wikipedia/commons/a/ab/Rain_thunder_and_birds.ogg",
        source_page="https://commons.wikimedia.org/wiki/File:Rain_thunder_and_birds.ogg",
        license="Public domain",
        attribution="ezwa via Wikimedia Commons",
    ),
    AudioLibraryEntry(
        id="forest-ambience",
        kind="soundscape",
        label="Forest Ambience",
        description="Forest wind, birds, and insects",
        filename="forest-ambience.ogg",
        duration_seconds=123,
        source_url="https://upload.wikimedia.org/wikipedia/commons/0/0a/20090610_0_ambience.ogg",
        source_page="https://commons.wikimedia.org/wiki/File:20090610_0_ambience.ogg",
        license="Public domain",
        attribution="nille via Wikimedia Commons",
    ),
    AudioLibraryEntry(
        id="ocean-waves",
        kind="soundscape",
        label="Ocean Waves",
        description="Waves rolling over small stones",
        filename="ocean-waves.ogg",
        duration_seconds=120,
        source_url="https://upload.wikimedia.org/wikipedia/commons/f/f1/Oceanwavescrushing.ogg",
        source_page="https://commons.wikimedia.org/wiki/File:Oceanwavescrushing.ogg",
        license="CC BY 3.0",
        attribution="Luftrum via Wikimedia Commons",
    ),
    AudioLibraryEntry(
        id="water-on-rocks",
        kind="soundscape",
        label="Water on Rocks",
        description="Shore water breaking on rocks",
        filename="water-on-rocks.ogg",
        duration_seconds=155,
        source_url="https://upload.wikimedia.org/wikipedia/commons/8/8a/Water_on_Rocks.ogg",
        source_page="https://commons.wikimedia.org/wiki/File:Water_on_Rocks.ogg",
        license="CC BY 3.0",
        attribution="Dsw4 via Wikimedia Commons",
    ),
    AudioLibraryEntry(
        id="yoga-flow",
        kind="yoga",
        label="Yoga Flow",
        description="Layered forest and water ambience",
        filename="yoga-flow.ogg",
        duration_seconds=123,
        # No source_url: this one is copied from the forest recording already on
        # disk. `derived_from` replaces the id check the router hardcoded.
        derived_from="forest-ambience.ogg",
        source_page="https://commons.wikimedia.org/wiki/File:20090610_0_ambience.ogg",
        license="CC BY 3.0 derivative",
        attribution="Mixed locally from nille and Dsw4 source recordings via Wikimedia Commons",
    ),
]
