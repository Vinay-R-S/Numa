"""Audio library business logic (NUMA-124, PLAN 2.1 / 5.2 / 21.1).

The download, derive and status helpers were module-level functions in
`router.py`. They are an `AudioLibraryService` now, with the catalog and the
audio directory injected through the constructor so a test can point it at a
temp dir instead of `server/audio/`.

Behavior is unchanged: same readiness threshold, same catalog order (the derived
yoga track is last, so the forest recording it copies is already on disk), same
temp-file-then-replace download, and the same per-item failure collection that
lets one bad source not stop the rest.
"""
from __future__ import annotations

import os
import shutil
import tempfile
import urllib.request
from collections.abc import Callable
from pathlib import Path

from ..core.base import BaseService
from .constants import AUDIO_LIBRARY, AUDIO_ROOT, MIN_AUDIO_BYTES
from .schemas import (
    AudioLibraryEnsureResult,
    AudioLibraryEntry,
    AudioLibraryFailure,
    AudioLibraryItem,
    AudioLibraryStatus,
)

DOWNLOAD_TIMEOUT_SECONDS = 45
DOWNLOAD_CHUNK_BYTES = 1024 * 256
DOWNLOAD_USER_AGENT = "Numa local audio downloader"


class AudioLibraryService(BaseService):
    """Keeps the local soundscape/yoga audio files present and reports on them."""

    def __init__(
        self,
        catalog: list[AudioLibraryEntry] | None = None,
        audio_root: Path | None = None,
        min_audio_bytes: int = MIN_AUDIO_BYTES,
    ) -> None:
        super().__init__()
        self.catalog = catalog if catalog is not None else AUDIO_LIBRARY
        self.audio_root = audio_root or AUDIO_ROOT
        self.min_audio_bytes = min_audio_bytes

    # ── Public API ───────────────────────────────────────────────────────────

    def status(self) -> AudioLibraryStatus:
        """What the client has available right now. Downloads nothing."""
        self._ensure_root()
        return AudioLibraryStatus(ok=True, items=self._items())

    def ensure(self) -> AudioLibraryEnsureResult:
        """Fetch or derive every missing track. Partial success is reported, not raised."""
        self._ensure_root()

        downloaded: list[str] = []
        failed: list[AudioLibraryFailure] = []

        for entry in self.catalog:
            if self._is_ready(entry.filename):
                continue

            try:
                if self._derive(entry):
                    downloaded.append(entry.id)
                    continue

                self._download(entry)
                downloaded.append(entry.id)
            except Exception as exc:
                self.log.warning("Audio download failed for %s: %s", entry.id, exc)
                failed.append(AudioLibraryFailure(id=entry.id, detail=str(exc)))

        return AudioLibraryEnsureResult(
            ok=not failed,
            downloaded=downloaded,
            failed=failed,
            items=self._items(),
        )

    # ── Disk state ───────────────────────────────────────────────────────────

    def _ensure_root(self) -> None:
        self.audio_root.mkdir(parents=True, exist_ok=True)

    def _path(self, filename: str) -> Path:
        return self.audio_root / filename

    def _is_ready(self, filename: str) -> bool:
        path = self._path(filename)
        return path.exists() and path.stat().st_size >= self.min_audio_bytes

    def _items(self) -> list[AudioLibraryItem]:
        return [self._item(entry) for entry in self.catalog]

    def _item(self, entry: AudioLibraryEntry) -> AudioLibraryItem:
        ready = self._is_ready(entry.filename)
        return AudioLibraryItem(
            id=entry.id,
            kind=entry.kind,
            label=entry.label,
            description=entry.description,
            filename=entry.filename,
            duration_seconds=entry.duration_seconds,
            url=f"/audio/{entry.filename}",
            ready=ready,
            license=entry.license,
            attribution=entry.attribution,
            source_page=entry.source_page,
            size_bytes=self._path(entry.filename).stat().st_size if ready else 0,
        )

    # ── Acquisition ──────────────────────────────────────────────────────────

    def _write_staged(self, filename: str, write: Callable[[Path], None]) -> bool:
        """Write to a temp file in the audio dir, then atomically replace the target.

        False means the result was under the readiness threshold and the target
        was left untouched. Nothing writes the final path directly: two `ensure`
        calls can overlap (the page prewarms while the player prepares), and
        `_is_ready` only measures size, so a half-written file at the real path
        would be reported ready and streamed as a corrupt track.
        """
        target = self._path(filename)
        fd, temp_name = tempfile.mkstemp(
            prefix=f"{target.stem}-", suffix=target.suffix, dir=self.audio_root
        )
        os.close(fd)
        temp_path = Path(temp_name)

        try:
            write(temp_path)
            if temp_path.stat().st_size < self.min_audio_bytes:
                return False

            temp_path.replace(target)
            return True
        finally:
            # `replace` moved it on success; on any failure this drops the partial.
            if temp_path.exists():
                temp_path.unlink()

    def _derive(self, entry: AudioLibraryEntry) -> bool:
        """Copy a local source track. False means "not derivable", so download instead."""
        if not entry.derived_from:
            return False

        source = self._path(entry.derived_from)
        if not self._is_ready(source.name):
            return False

        return self._write_staged(entry.filename, lambda temp: shutil.copyfile(source, temp))

    def _download(self, entry: AudioLibraryEntry) -> None:
        if not entry.source_url:
            raise RuntimeError(f"No download source configured for {entry.filename}")

        if not self._write_staged(entry.filename, lambda temp: self._stream(entry.source_url, temp)):
            raise RuntimeError(f"Downloaded file too small: {entry.filename}")

    def _stream(self, source_url: str, target: Path) -> None:
        request = urllib.request.Request(
            source_url,
            headers={"User-Agent": DOWNLOAD_USER_AGENT},
        )
        with urllib.request.urlopen(request, timeout=DOWNLOAD_TIMEOUT_SECONDS) as response:
            with target.open("wb") as handle:
                while True:
                    chunk = response.read(DOWNLOAD_CHUNK_BYTES)
                    if not chunk:
                        break
                    handle.write(chunk)


audio_library_service = AudioLibraryService()
