"""Auth dependencies: request-scoped identity and authorization gates.

`get_current_user` proves *who* is calling. `require_admin` (NUMA-125 P6, PLAN 8)
adds the *what may they do* half the app never had: an allowlist for endpoints
that write server-wide configuration rather than one user's own data.

The allowlist is an env var rather than a `profiles.role` column on purpose. The
JWT carries only `sub`/`email`/`full_name`, so a DB-backed role would need a
migration, a promote path for the first admin and re-issued tokens; server-wide
config is an operator concern, and the operator already owns the `.env`.

Per-user settings are deliberately NOT gated. Anyone signed in still picks their
own provider, model and API key through `PUT /ai-settings`, which is scoped by
`user_id` and stores that key encrypted per user.
"""
import logging
import os

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError

from .service import verify_jwt

log = logging.getLogger(__name__)

_bearer = HTTPBearer()

#: Set once the unconfigured-admin error has been logged, so a client polling an
#: admin route cannot flood the log with the same line.
_unconfigured_logged = False

#: Comma-separated email allowlist. Empty means no one is an admin (fail closed).
ADMIN_EMAILS_ENV = "NUMA_ADMIN_EMAILS"

ADMIN_UNCONFIGURED_DETAIL = (
    "Admin access is not configured on this server. Set NUMA_ADMIN_EMAILS in the "
    "server .env to the email addresses allowed to change server-wide settings."
)
ADMIN_REQUIRED_DETAIL = "Admin access is required to change server-wide settings."


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
) -> dict:
    """FastAPI dependency - validates Bearer JWT and returns its payload."""
    try:
        payload = verify_jwt(credentials.credentials)
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token.",
            headers={"WWW-Authenticate": "Bearer"},
        )


def admin_emails() -> frozenset[str]:
    """The allowlist, lowercased and trimmed.

    Read from `os.environ` on each call rather than cached at import, so tests can
    set it and a reload picks it up. Editing the `.env` file itself still needs a
    restart: `auth.service` loads it once at import.
    """
    raw = os.getenv(ADMIN_EMAILS_ENV, "")
    return frozenset(entry.strip().lower() for entry in raw.split(",") if entry.strip())


async def require_admin(current_user: dict = Depends(get_current_user)) -> dict:
    """Authenticated *and* on the allowlist. Fails closed when the var is unset.

    Denials log `sub` rather than the email: PLAN 8 bans PII in logs, and the
    user id is the pseudonymous identifier the rest of the app already logs.
    """
    allowlist = admin_emails()
    if not allowlist:
        global _unconfigured_logged
        if not _unconfigured_logged:
            _unconfigured_logged = True
            log.error("%s is unset; refusing all admin-only requests", ADMIN_EMAILS_ENV)
        raise HTTPException(status.HTTP_403_FORBIDDEN, ADMIN_UNCONFIGURED_DETAIL)

    email = str(current_user.get("email") or "").strip().lower()
    if email not in allowlist:
        log.warning("Admin-only request refused for user %s", current_user.get("sub"))
        raise HTTPException(status.HTTP_403_FORBIDDEN, ADMIN_REQUIRED_DETAIL)

    return current_user
