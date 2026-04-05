"""Slack OAuth login and callback."""
from fastapi import APIRouter, Depends
from fastapi.responses import RedirectResponse

from app.auth import exchange_slack_code, upsert_user_from_slack, create_access_token, get_current_user
from app.config import settings
from app.models import UserOut

router = APIRouter(prefix="/auth", tags=["auth"])

SLACK_OAUTH_URL = (
    "https://slack.com/oauth/v2/authorize"
    "?scope=channels:history,channels:read,chat:write,users:read,users:read.email"
    "&user_scope=identity.basic,identity.email,identity.avatar"
    "&client_id={client_id}"
    "&redirect_uri={redirect_uri}"
)


@router.get("/slack")
async def slack_login():
    """Redirect browser to Slack OAuth consent screen."""
    url = SLACK_OAUTH_URL.format(
        client_id=settings.SLACK_CLIENT_ID,
        redirect_uri=settings.SLACK_REDIRECT_URI,
    )
    return RedirectResponse(url=url)


@router.get("/slack/callback")
async def slack_callback(code: str, state: str | None = None):
    """
    Slack redirects here after user consent.
    Exchange code → token → upsert user → issue JWT → redirect to frontend.
    """
    slack_data = await exchange_slack_code(code)
    user = await upsert_user_from_slack(slack_data)
    token = create_access_token({"sub": user.id, "slack_id": user.slack_user_id})

    # Redirect to frontend with JWT in query string (frontend stores in memory/localStorage)
    frontend_url = "http://localhost:5173"
    return RedirectResponse(url=f"{frontend_url}/auth/callback?token={token}")


@router.get("/me", response_model=UserOut)
async def get_me(current_user: UserOut = Depends(get_current_user)):
    """Return the authenticated NUMA user."""
    return current_user
