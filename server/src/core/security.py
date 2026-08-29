"""API-key encryption (NUMA-102, NUMA-128 P6, PLAN 5.1 / 8).

The Fernet implementation lives here now; `core.llm_factory` re-exports it so
existing import paths keep working. PLAN 5.1 always intended this direction.

What changed on NUMA-128 is the failure behavior. The old derivation generated an
*ephemeral* key when `NUMA_ENCRYPTION_KEY` was unset, which meant a running server
happily encrypted API keys that nothing could ever decrypt again - silent data
loss - and, after a restart, silently fell back to the shared env-var provider
keys because every decrypt raised. A malformed key was no better: it surfaced as
a 500 from the settings page on the first save, with no hint of the cause.

There is no ephemeral key any more. A key is either present and valid, or the
operation fails with a message naming the variable and how to generate one.
"""
from __future__ import annotations

import logging
import os
from cryptography.fernet import Fernet

log = logging.getLogger(__name__)

ENCRYPTION_KEY_ENV = "NUMA_ENCRYPTION_KEY"

_GENERATE_HINT = (
    'Generate one with: python -c "from cryptography.fernet import Fernet; '
    'print(Fernet.generate_key().decode())"'
)
_MISSING_MESSAGE = f"{ENCRYPTION_KEY_ENV} is not set. {_GENERATE_HINT}"
_INVALID_MESSAGE = (
    f"{ENCRYPTION_KEY_ENV} is not a valid Fernet key (it must be 32 url-safe "
    f"base64-encoded bytes). {_GENERATE_HINT}"
)


class EncryptionKeyError(RuntimeError):
    """The encryption key is missing or malformed. Never raised for bad ciphertext."""


__all__ = [
    "ENCRYPTION_KEY_ENV",
    "EncryptionKeyError",
    "decrypt_api_key",
    "encrypt_api_key",
    "encryption_key_configured",
    "generate_encryption_key",
    "get_fernet",
    "verify_encryption_key",
]

#: (raw key, cipher) so a changed environment is not served from a stale cache.
_cached: tuple[str, Fernet] | None = None


def _raw_key() -> str:
    return os.getenv(ENCRYPTION_KEY_ENV, "").strip()


def encryption_key_configured() -> bool:
    return bool(_raw_key())


def get_fernet() -> Fernet:
    """The configured cipher, or `EncryptionKeyError` explaining what to fix."""
    global _cached

    raw = _raw_key()
    if not raw:
        raise EncryptionKeyError(_MISSING_MESSAGE)

    if _cached is not None and _cached[0] == raw:
        return _cached[1]

    try:
        fernet = Fernet(raw.encode())
    except (ValueError, TypeError) as exc:
        raise EncryptionKeyError(_INVALID_MESSAGE) from exc

    _cached = (raw, fernet)
    return fernet


def encrypt_api_key(plain: str) -> str:
    return get_fernet().encrypt(plain.encode()).decode()


def decrypt_api_key(token: str) -> str:
    return get_fernet().decrypt(token.encode()).decode()


def generate_encryption_key() -> str:
    """A fresh key, for setup scripts and the error messages above."""
    return Fernet.generate_key().decode()


def verify_encryption_key(*, encrypted_rows_exist: bool) -> None:
    """Boot check (PLAN 8). Raises rather than letting the fault reach a request.

    A malformed key can never work, so it fails the boot outright. A missing key
    fails the boot only when there is already ciphertext to lose access to;
    otherwise a fresh install is allowed to start, and the first attempt to
    encrypt reports the same message rather than inventing a throwaway key.

    `encrypted_rows_exist` is keyword-only with no default on purpose: a security
    check must not have a permissive value a caller can fall into by omission.
    """
    if not encryption_key_configured():
        if encrypted_rows_exist:
            raise EncryptionKeyError(
                f"{_MISSING_MESSAGE} Stored API keys already exist and cannot be "
                "decrypted without it, so the server will not start."
            )
        log.warning("%s Until it is set, saving an API key is refused.", _MISSING_MESSAGE)
        return

    get_fernet()
    log.info("%s is present and valid.", ENCRYPTION_KEY_ENV)
