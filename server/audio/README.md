# Local audio library

This folder stores ambient audio downloaded by the backend for the Mental Peace page.

The backend checks this folder through `POST /audio-library/ensure`. If a file already exists and is large enough to be valid, it is reused. Missing files are downloaded once from the copyright-free source URLs configured in `server/src/audio_library/router.py`.
