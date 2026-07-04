import os

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status

from .schemas import SignUpRequest, SignInRequest, TokenResponse, UserResponse, ExchangeRequest
from .service import sign_up, sign_in, exchange_supabase_token, JWT_EXPIRE_SECONDS
from .dependencies import get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])


# ── Email / Password ──────────────────────────────────────────────────────────

@router.post("/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def signup(body: SignUpRequest):
    """Register with email + password. Returns a 7-day JWT."""
    try:
        result = sign_up(body.email, body.password, body.full_name)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return TokenResponse(access_token=result["token"], expires_in=JWT_EXPIRE_SECONDS)


@router.post("/signin", response_model=TokenResponse)
def signin(body: SignInRequest):
    """Sign in with email + password. Returns a 7-day JWT."""
    try:
        result = sign_in(body.email, body.password)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
    return TokenResponse(access_token=result["token"], expires_in=JWT_EXPIRE_SECONDS)


# ── OAuth token exchange (Google / GitHub) ────────────────────────────────────

@router.post("/exchange", response_model=TokenResponse)
def exchange(body: ExchangeRequest):
    """
    Accept the Supabase access_token that the frontend receives after OAuth
    (Google / GitHub) and return our own 7-day JWT.
    """
    try:
        result = exchange_supabase_token(body.supabase_token)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
    return TokenResponse(access_token=result["token"], expires_in=JWT_EXPIRE_SECONDS)


# ── Protected endpoints ───────────────────────────────────────────────────────

@router.get("/me", response_model=UserResponse)
def me(current_user: dict = Depends(get_current_user)):
    """Return the currently authenticated user's profile."""
    return UserResponse(
        id=current_user["sub"],
        email=current_user["email"],
        full_name=current_user.get("full_name") or None,
    )


@router.post("/signout")
def signout():
    """
    Stateless sign-out - the client simply discards its JWT.
    Supabase session tokens are short-lived; our JWT expiry handles revocation.
    """
    return {"message": "Signed out successfully."}


@router.post("/bootstrap")
def bootstrap_integrations(
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
):
    """
    Post-login integration bootstrap.

    This endpoint starts sync for services that are already authorized and returns
    the next OAuth action for services that still need explicit user consent.
    Slack/GitHub cannot be silently connected from Google sign-in because they are
    separate providers with separate consent screens.
    """
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="User session is invalid")

    services: dict = {}
    next_action = None

    # Google Calendar + Google Fit share the app's Google OAuth flow/scopes.
    try:
        from ..calendar.router import GOOGLE_OAUTH_REDIRECT_URI, _build_oauth_state
        from ..calendar.service import (
            build_google_oauth_authorization_url,
            get_calendar_service,
            has_calendar_credentials,
        )

        google_connected = has_calendar_credentials(user_id)
        google_valid = False
        google_reason = None
        if google_connected:
            try:
                svc = get_calendar_service(user_id=user_id)
                svc.calendarList().list(maxResults=1).execute()
                google_valid = True
            except Exception as exc:
                google_reason = str(exc)

        services["google"] = {
            "connected": google_connected,
            "valid": google_valid,
            "detail": google_reason,
        }

        if not google_valid:
            state = _build_oauth_state(user_id)
            next_action = {
                "service": "google",
                "type": "oauth_redirect",
                "authorization_url": build_google_oauth_authorization_url(
                    redirect_uri=GOOGLE_OAUTH_REDIRECT_URI,
                    state=state,
                ),
            }
    except Exception as exc:
        services["google"] = {"connected": False, "valid": False, "detail": str(exc)}

    # Slack requires Slack OAuth consent.
    try:
        from ..slack_agent.router import _build_slack_authorization_url
        from .repository import auth_repository

        slack_connected = auth_repository.slack_auth_exists(user_id)

        bot_configured = bool((os.getenv("SLACK_BOT_TOKEN") or "").strip())
        services["slack"] = {
            "connected": slack_connected,
            "bot_configured": bot_configured,
        }
        if next_action is None and not slack_connected:
            services["slack"]["authorization_url"] = _build_slack_authorization_url(user_id)
            next_action = {
                "service": "slack",
                "type": "oauth_redirect",
                "authorization_url": services["slack"]["authorization_url"],
            }
    except Exception as exc:
        services["slack"] = {"connected": False, "detail": str(exc)}

    # GitHub requires GitHub OAuth or token consent.
    try:
        from ..github_agent.router import _get_github_config, _get_github_token, _oauth_states, GITHUB_OAUTH_URL
        import secrets
        from urllib.parse import urlencode

        github_connected = bool(_get_github_token(user_id))
        services["github"] = {"connected": github_connected}
        client_id, _, redirect_uri = _get_github_config()
        if next_action is None and not github_connected and client_id:
            state = secrets.token_urlsafe(32)
            _oauth_states[state] = user_id
            params = {
                "client_id": client_id,
                "redirect_uri": redirect_uri,
                "scope": "repo read:user user:email",
                "state": state,
            }
            authorization_url = f"{GITHUB_OAUTH_URL}?{urlencode(params)}"
            services["github"]["authorization_url"] = authorization_url
            next_action = {
                "service": "github",
                "type": "oauth_redirect",
                "authorization_url": authorization_url,
            }
    except Exception as exc:
        services["github"] = {"connected": False, "detail": str(exc)}

    leetcode_username = (os.getenv("LEETCODE_USERNAME") or "").strip()
    services["leetcode"] = {
        "connected": bool(leetcode_username),
        "detail": "username configured" if leetcode_username else "LeetCode requires a username, not OAuth.",
    }

    # Always start best-effort sync in the background for whatever is connected now.
    try:
        from ..data_sync import fetch_latest_for_user

        background_tasks.add_task(fetch_latest_for_user, user_id)
        sync_started = True
    except Exception:
        sync_started = False

    return {
        "ok": True,
        "sync_started": sync_started,
        "services": services,
        "next_action": next_action,
    }
