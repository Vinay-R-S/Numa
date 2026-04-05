"""
JWT-based authentication helpers and FastAPI dependency.
Auth flow:
  1. User hits /auth/slack  → redirected to Slack OAuth
  2. Slack redirects to /auth/slack/callback with ?code=...
  3. We exchange code for Slack token, upsert user in Supabase
  4. We issue our own JWT and return it to the frontend
  5. All protected routes use Depends(get_current_user)
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt

from app.config import settings
from app.database import get_supabase
from app.models import UserOut

logger = logging.getLogger(__name__)

_bearer = HTTPBearer(auto_error=True)

MOOD_SCORES = {"great": 5, "good": 4, "okay": 3, "low": 2, "bad": 1}


# ── Token helpers ─────────────────────────────────────────────────────────────

def create_access_token(payload: dict) -> str:
    data = payload.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    data.update({"exp": expire})
    return jwt.encode(data, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


# ── FastAPI dependency ────────────────────────────────────────────────────────

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
) -> UserOut:
    payload = decode_token(credentials.credentials)
    user_id: Optional[str] = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    db = get_supabase()
    resp = db.table("users").select("*").eq("id", user_id).single().execute()
    if not resp.data:
        raise HTTPException(status_code=404, detail="User not found")

    return UserOut(**resp.data)


# ── Slack OAuth exchange ──────────────────────────────────────────────────────

async def exchange_slack_code(code: str) -> dict:
    """Exchange Slack OAuth code for access token and user info."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://slack.com/api/oauth.v2.access",
            data={
                "client_id": settings.SLACK_CLIENT_ID,
                "client_secret": settings.SLACK_CLIENT_SECRET,
                "code": code,
                "redirect_uri": settings.SLACK_REDIRECT_URI,
            },
        )
    data = resp.json()
    if not data.get("ok"):
        raise HTTPException(status_code=400, detail=f"Slack OAuth error: {data.get('error')}")
    return data


async def upsert_user_from_slack(slack_data: dict) -> UserOut:
    """Create or update user record from Slack OAuth response."""
    authed_user = slack_data.get("authed_user", {})
    team = slack_data.get("team", {})

    slack_user_id = authed_user.get("id")
    slack_team_id = team.get("id")
    access_token = authed_user.get("access_token") or slack_data.get("access_token")

    # Fetch Slack user profile for display info
    profile = {}
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(
                "https://slack.com/api/users.info",
                headers={"Authorization": f"Bearer {access_token}"},
                params={"user": slack_user_id},
            )
        user_data = r.json()
        if user_data.get("ok"):
            profile = user_data["user"].get("profile", {})
    except Exception as exc:
        logger.warning(f"Could not fetch Slack profile: {exc}")

    upsert_payload = {
        "slack_user_id": slack_user_id,
        "slack_team_id": slack_team_id,
        "display_name": profile.get("display_name") or authed_user.get("name"),
        "real_name": profile.get("real_name"),
        "email": profile.get("email"),
        "avatar_url": profile.get("image_72"),
        "access_token": access_token,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

    db = get_supabase()
    # Upsert on slack_user_id
    result = (
        db.table("users")
        .upsert(upsert_payload, on_conflict="slack_user_id")
        .execute()
    )
    user_row = result.data[0]
    return UserOut(**user_row)
