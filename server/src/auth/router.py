import logging
import os

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status

from .schemas import SignUpRequest, SignInRequest, TokenResponse, UserResponse, ExchangeRequest
from .service import sign_up, sign_in, exchange_supabase_token, JWT_EXPIRE_SECONDS
from .dependencies import get_current_user

log = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])

# Bootstrap probes third-party services, so its failures carry provider hosts,
# token-endpoint bodies and driver text. `str(exc)` in the JSON body walked
# straight past the NUMA-134 redaction, which only filters log records. The
# reason is logged; the caller is told a service could not be checked
# (NUMA-142 P6, PLAN 8).
_PROBE_FAILED_DETAIL = "Could not check this integration"


def _probe_failed(service: str, exc: Exception) -> str:
    log.warning("Bootstrap probe failed for %s: %s", service, exc, exc_info=True)
    return _PROBE_FAILED_DETAIL


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
                google_reason = _probe_failed("google", exc)

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
        services["google"] = {
            "connected": False,
            "valid": False,
            "detail": _probe_failed("google", exc),
        }

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
        services["slack"] = {"connected": False, "detail": _probe_failed("slack", exc)}

    # GitHub requires GitHub OAuth or token consent.
    try:
        from ..github_agent.router import _get_github_config, _get_github_token
        from ..github_agent.service import github_service

        github_connected = bool(_get_github_token(user_id))
        services["github"] = {"connected": github_connected}
        client_id, _, _ = _get_github_config()
        if next_action is None and not github_connected and client_id:
            # The service owns the URL and the signed state; this route used to
            # hand-roll both and write into a module-global dict that the
            # callback could not see under a second worker (NUMA-142 P6).
            authorization_url = github_service.build_authorization_url(user_id)
            services["github"]["authorization_url"] = authorization_url
            next_action = {
                "service": "github",
                "type": "oauth_redirect",
                "authorization_url": authorization_url,
            }
    except Exception as exc:
        services["github"] = {"connected": False, "detail": _probe_failed("github", exc)}

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
