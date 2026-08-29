import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from jose import jwt, JWTError
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

# ── Config ────────────────────────────────────────────────────────────────────
SUPABASE_URL: str = os.environ["SUPABASE_URL"]
SUPABASE_ANON_KEY: str = os.environ["SUPABASE_ANON_KEY"]
SUPABASE_SERVICE_ROLE_KEY: str = os.environ["SUPABASE_SERVICE_ROLE_KEY"]

JWT_SECRET: str = os.environ["JWT_SECRET"]
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_DAYS = 7
JWT_EXPIRE_SECONDS = JWT_EXPIRE_DAYS * 24 * 3600

# ── Supabase clients ──────────────────────────────────────────────────────────
# Anon client - used for sign-up / sign-in (respects RLS)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

# Service-role client - used to verify arbitrary tokens (admin operations)
supabase_admin: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)


# ── JWT helpers ───────────────────────────────────────────────────────────────

def create_jwt(user_id: str, email: str, full_name: Optional[str] = None) -> str:
    """Create a signed JWT with a 7-day expiry."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "email": email,
        "full_name": full_name or "",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(days=JWT_EXPIRE_DAYS)).timestamp()),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def verify_jwt(token: str) -> dict:
    """Decode and verify a JWT; raises JWTError on failure."""
    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])


# ── Profile helpers ──────────────────────────────────────────────────────────

def _upsert_profile(user_id: str, full_name: str | None) -> None:
    """
    Insert or update a row in public.profiles.
    Uses the service-role client so RLS is bypassed.
    """
    try:
        supabase_admin.table("profiles").upsert(
            {
                "id": user_id,
                "full_name": full_name or "",
            },
            on_conflict="id",
        ).execute()
    except Exception as exc:
        import logging
        logging.getLogger(__name__).error("profile upsert failed: %s", exc)


# ── Auth operations ───────────────────────────────────────────────────────────

def sign_up(email: str, password: str, full_name: Optional[str] = None) -> dict:
    """Register a new user via Supabase and return our JWT + user info.

    Only a confirmed sign-up (one Supabase answers with a session) gets a token;
    everything else is told to confirm first, which is also the answer an already
    registered address gets, so this does not leak which addresses exist.
    """
    response = supabase.auth.sign_up(
        {
            "email": email,
            "password": password,
            "options": {"data": {"full_name": full_name or ""}},
        }
    )
    if response.user is None:
        raise ValueError("Sign-up failed. The email may already be registered.")

    user = response.user
    display_name = (user.user_metadata or {}).get("full_name")
    _upsert_profile(str(user.id), display_name)

    # Supabase returns a user with no session when the address still has to be
    # confirmed, and an obfuscated placeholder user when the address is already
    # registered. Minting our JWT off `response.user` alone therefore proved
    # nothing about who owns the address - and since NUMA-125 keys admin access
    # on the email claim, that let anyone claim an allowlisted address by
    # signing up with it first. No session, no token (NUMA-125 P6, PLAN 8).
    if response.session is None:
        raise ValueError(
            "Check your email to confirm your account, then sign in."
        )

    token = create_jwt(
        str(user.id),
        user.email,
        display_name,
    )
    return {
        "token": token,
        "user": {
            "id": str(user.id),
            "email": user.email,
            "full_name": display_name,
        },
    }


def sign_in(email: str, password: str) -> dict:
    """Authenticate an existing user and return our JWT + user info."""
    response = supabase.auth.sign_in_with_password(
        {"email": email, "password": password}
    )
    if response.user is None:
        raise ValueError("Invalid email or password.")

    user = response.user
    token = create_jwt(
        str(user.id),
        user.email,
        (user.user_metadata or {}).get("full_name"),
    )
    return {
        "token": token,
        "user": {
            "id": str(user.id),
            "email": user.email,
            "full_name": (user.user_metadata or {}).get("full_name"),
        },
    }


def exchange_supabase_token(supabase_access_token: str) -> dict:
    """
    Verify a Supabase access_token (obtained via OAuth on the frontend)
    using the admin client, then issue our own JWT.
    """
    response = supabase_admin.auth.get_user(supabase_access_token)
    if response.user is None:
        raise ValueError("Invalid Supabase token.")

    user = response.user
    metadata = user.user_metadata or {}
    full_name = metadata.get("full_name") or metadata.get("name") or ""
    _upsert_profile(str(user.id), full_name)
    token = create_jwt(str(user.id), user.email, full_name)
    return {
        "token": token,
        "user": {
            "id": str(user.id),
            "email": user.email,
            "full_name": full_name,
        },
    }
