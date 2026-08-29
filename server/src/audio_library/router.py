"""
Audio Library Router
====================
Endpoints
---------
GET  /audio-library/status  - catalog plus on-disk readiness, downloads nothing
POST /audio-library/ensure  - fetch or derive every missing track

Thin routing layer (NUMA-124, PLAN 2.1 / 8 / 18 / 21.1): the catalog lives in
constants.py, the payload models in schemas.py, and the download/derive work in
the `Depends`-injected `AudioLibraryService`.

Both routes now require a bearer token. They were the one unauthenticated router
in the app (PLAN 8), which let any caller drive outbound Wikimedia downloads and
writes into `server/audio/`. The client already sent the token on `ensure`; the
router simply ignored it. The `/audio` static mount is unchanged: the `<audio>`
element streams files directly and carries no header.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends

from ..auth.dependencies import get_current_user
from .constants import AUDIO_LIBRARY  # noqa: F401  re-exported for existing import paths
from .schemas import AudioLibraryEnsureResult, AudioLibraryStatus
from .service import AudioLibraryService, audio_library_service

log = logging.getLogger(__name__)

router = APIRouter(
    prefix="/audio-library",
    tags=["audio-library"],
    dependencies=[Depends(get_current_user)],
)


def get_audio_library_service() -> AudioLibraryService:
    return audio_library_service


@router.get("/status", response_model=AudioLibraryStatus, summary="Local audio readiness")
def audio_status(
    service: AudioLibraryService = Depends(get_audio_library_service),
) -> AudioLibraryStatus:
    return service.status()


@router.post("/ensure", response_model=AudioLibraryEnsureResult, summary="Download missing audio")
def ensure_audio_library(
    service: AudioLibraryService = Depends(get_audio_library_service),
) -> AudioLibraryEnsureResult:
    return service.ensure()
