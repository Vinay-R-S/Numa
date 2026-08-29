"""Pydantic schemas for the audio library API (NUMA-124, PLAN 21.1 / 22.1).

The two routes used to return bare `dict[str, object]` with no `response_model`,
which is why the client validates them with a `looseObject` zod schema. The
payloads are declared here instead, so the shape the client mirrors is the shape
FastAPI enforces and publishes in the OpenAPI document.
"""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel

AudioKind = Literal["soundscape", "yoga"]


class AudioLibraryEntry(BaseModel):
    """A catalog row: what the track is, and where the bytes come from."""

    id: str
    kind: AudioKind
    label: str
    description: str
    filename: str
    duration_seconds: int
    license: str
    attribution: str
    source_page: str
    #: Remote download source. Absent for a locally derived track.
    source_url: Optional[str] = None
    #: Filename of an already-downloaded track this one is copied from.
    derived_from: Optional[str] = None


class AudioLibraryItem(BaseModel):
    """A catalog row plus its on-disk state, as served to the client."""

    id: str
    kind: AudioKind
    label: str
    description: str
    filename: str
    duration_seconds: int
    url: str
    ready: bool
    license: str
    attribution: str
    source_page: str
    size_bytes: int


class AudioLibraryFailure(BaseModel):
    id: str
    detail: str


class AudioLibraryStatus(BaseModel):
    ok: bool = True
    items: list[AudioLibraryItem]


class AudioLibraryEnsureResult(BaseModel):
    """`ok` is false when at least one track could not be fetched or derived."""

    ok: bool
    downloaded: list[str]
    failed: list[AudioLibraryFailure]
    items: list[AudioLibraryItem]
