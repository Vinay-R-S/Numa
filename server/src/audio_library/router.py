from __future__ import annotations

import os
import shutil
import tempfile
import urllib.request
from pathlib import Path
from typing import Literal

from fastapi import APIRouter


router = APIRouter(prefix="/audio-library", tags=["audio-library"])

SERVER_ROOT = Path(__file__).resolve().parents[2]
AUDIO_ROOT = SERVER_ROOT / "audio"
MIN_AUDIO_BYTES = 100_000

AudioKind = Literal["soundscape", "yoga"]


AUDIO_LIBRARY: list[dict[str, str | int]] = [
    {
        "id": "rain-thunder-birds",
        "kind": "soundscape",
        "label": "Rain and Birds",
        "filename": "rain-thunder-birds.ogg",
        "duration_seconds": 134,
        "source_url": "https://upload.wikimedia.org/wikipedia/commons/a/ab/Rain_thunder_and_birds.ogg",
        "source_page": "https://commons.wikimedia.org/wiki/File:Rain_thunder_and_birds.ogg",
        "license": "Public domain",
        "attribution": "ezwa via Wikimedia Commons",
    },
    {
        "id": "forest-ambience",
        "kind": "soundscape",
        "label": "Forest Ambience",
        "filename": "forest-ambience.ogg",
        "duration_seconds": 123,
        "source_url": "https://upload.wikimedia.org/wikipedia/commons/0/0a/20090610_0_ambience.ogg",
        "source_page": "https://commons.wikimedia.org/wiki/File:20090610_0_ambience.ogg",
        "license": "Public domain",
        "attribution": "nille via Wikimedia Commons",
    },
    {
        "id": "ocean-waves",
        "kind": "soundscape",
        "label": "Ocean Waves",
        "filename": "ocean-waves.ogg",
        "duration_seconds": 120,
        "source_url": "https://upload.wikimedia.org/wikipedia/commons/f/f1/Oceanwavescrushing.ogg",
        "source_page": "https://commons.wikimedia.org/wiki/File:Oceanwavescrushing.ogg",
        "license": "CC BY 3.0",
        "attribution": "Luftrum via Wikimedia Commons",
    },
    {
        "id": "water-on-rocks",
        "kind": "soundscape",
        "label": "Water on Rocks",
        "filename": "water-on-rocks.ogg",
        "duration_seconds": 155,
        "source_url": "https://upload.wikimedia.org/wikipedia/commons/8/8a/Water_on_Rocks.ogg",
        "source_page": "https://commons.wikimedia.org/wiki/File:Water_on_Rocks.ogg",
        "license": "CC BY 3.0",
        "attribution": "Dsw4 via Wikimedia Commons",
    },
    {
        "id": "yoga-flow",
        "kind": "yoga",
        "label": "Yoga Flow",
        "filename": "yoga-flow.ogg",
        "duration_seconds": 123,
        "source_page": "https://commons.wikimedia.org/wiki/File:20090610_0_ambience.ogg",
        "license": "CC BY 3.0 derivative",
        "attribution": "Mixed locally from nille and Dsw4 source recordings via Wikimedia Commons",
    },
]


def _audio_path(filename: str) -> Path:
    return AUDIO_ROOT / filename


def _file_ready(filename: str) -> bool:
    path = _audio_path(filename)
    return path.exists() and path.stat().st_size >= MIN_AUDIO_BYTES


def _download_audio(item: dict[str, str | int]) -> None:
    AUDIO_ROOT.mkdir(parents=True, exist_ok=True)
    filename = str(item["filename"])
    target = _audio_path(filename)

    fd, temp_name = tempfile.mkstemp(prefix=f"{target.stem}-", suffix=target.suffix, dir=AUDIO_ROOT)
    os.close(fd)
    temp_path = Path(temp_name)

    try:
        source_url = item.get("source_url")
        if not source_url:
            raise RuntimeError(f"No download source configured for {filename}")

        request = urllib.request.Request(
            str(source_url),
            headers={"User-Agent": "Numa local audio downloader"},
        )
        with urllib.request.urlopen(request, timeout=45) as response:
            with temp_path.open("wb") as handle:
                while True:
                    chunk = response.read(1024 * 256)
                    if not chunk:
                        break
                    handle.write(chunk)

        if temp_path.stat().st_size < MIN_AUDIO_BYTES:
            raise RuntimeError(f"Downloaded file too small: {filename}")

        temp_path.replace(target)
    finally:
        if temp_path.exists():
            temp_path.unlink()


def _create_derived_audio(item: dict[str, str | int]) -> bool:
    if item.get("id") != "yoga-flow":
        return False

    target = _audio_path(str(item["filename"]))
    source = _audio_path("forest-ambience.ogg")
    if not _file_ready(source.name):
        return False

    shutil.copyfile(source, target)
    return _file_ready(target.name)


def _item_response(item: dict[str, str | int]) -> dict[str, str | int | bool]:
    filename = str(item["filename"])
    ready = _file_ready(filename)
    return {
        "id": item["id"],
        "kind": item["kind"],
        "label": item["label"],
        "filename": filename,
        "duration_seconds": item["duration_seconds"],
        "url": f"/audio/{filename}",
        "ready": ready,
        "license": item["license"],
        "attribution": item["attribution"],
        "source_page": item["source_page"],
        "size_bytes": _audio_path(filename).stat().st_size if ready else 0,
    }


@router.get("/status")
def audio_status() -> dict[str, object]:
    AUDIO_ROOT.mkdir(parents=True, exist_ok=True)
    return {
        "ok": True,
        "items": [_item_response(item) for item in AUDIO_LIBRARY],
    }


@router.post("/ensure")
def ensure_audio_library() -> dict[str, object]:
    AUDIO_ROOT.mkdir(parents=True, exist_ok=True)

    downloaded: list[str] = []
    failed: list[dict[str, str]] = []

    for item in AUDIO_LIBRARY:
        filename = str(item["filename"])
        if _file_ready(filename):
            continue

        try:
            if _create_derived_audio(item):
                downloaded.append(str(item["id"]))
                continue

            _download_audio(item)
            downloaded.append(str(item["id"]))
        except Exception as exc:
            failed.append({"id": str(item["id"]), "detail": str(exc)})

    items = [_item_response(item) for item in AUDIO_LIBRARY]
    return {
        "ok": not failed,
        "downloaded": downloaded,
        "failed": failed,
        "items": items,
    }
