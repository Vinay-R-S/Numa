"""Google Calendar OAuth, credentials and token-path helpers (NUMA-104 P3, PLAN 16.1).

Leaf module: stdlib + Google libs only, no cross-module calendar imports.
Extracted verbatim from calendar/service.py; service.py re-exports these names.
"""
import os
import json
import importlib
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

log = logging.getLogger(__name__)

GOOGLE_SCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/fitness.activity.read",
    "https://www.googleapis.com/auth/fitness.sleep.read",
    "https://www.googleapis.com/auth/fitness.location.read",
    "https://www.googleapis.com/auth/fitness.heart_rate.read",
]


def _require_google_calendar_deps():
    try:
        request_module     = importlib.import_module("google.auth.transport.requests")
        credentials_module = importlib.import_module("google.oauth2.credentials")
        flow_module        = importlib.import_module("google_auth_oauthlib.flow")
        discovery_module   = importlib.import_module("googleapiclient.discovery")

        Request     = getattr(request_module,     "Request")
        Credentials = getattr(credentials_module, "Credentials")
        Flow        = getattr(flow_module,        "Flow")
        build       = getattr(discovery_module,   "build")
    except ImportError as exc:
        raise RuntimeError(
            "Google Calendar dependencies are missing. Install google-api-python-client, google-auth, and google-auth-oauthlib."
        ) from exc

    return Request, Credentials, Flow, build


def _candidate_credentials_paths() -> List[Path]:
    explicit = os.getenv("GOOGLE_CALENDAR_CREDENTIALS_FILE")
    if explicit:
        return [Path(explicit)]

    workspace_root = Path(__file__).resolve().parents[3]
    return [
        Path.cwd() / "gCalender_credentials.json",
        workspace_root / "server" / "gCalender_credentials.json",
        workspace_root / "GoogleCalender-Agent" / "Backend-agent" / "gCalender_credentials.json",
    ]


def _resolve_credentials_file() -> Path:
    for candidate in _candidate_credentials_paths():
        if candidate.exists():
            return candidate

    raise RuntimeError(
        "Google credentials file not found. Set GOOGLE_CALENDAR_CREDENTIALS_FILE or place gCalender_credentials.json in server/."
    )


def _legacy_token_file() -> Path:
    explicit = os.getenv("GOOGLE_CALENDAR_TOKEN_FILE")
    if explicit:
        return Path(explicit)

    workspace_root = Path(__file__).resolve().parents[3]
    return workspace_root / "server" / "token.json"


def _token_dir() -> Path:
    explicit = os.getenv("GOOGLE_CALENDAR_TOKEN_DIR")
    if explicit:
        return Path(explicit)

    workspace_root = Path(__file__).resolve().parents[3]
    return workspace_root / "server" / "apiConfig" / "google"


def _user_token_file(user_id: str) -> Path:
    safe_user_id = "".join(ch for ch in user_id if ch.isalnum() or ch in ("-", "_"))
    if not safe_user_id:
        raise RuntimeError("Invalid user id for Google token storage")
    return _token_dir() / f"{safe_user_id}.json"


def _load_client_config() -> Dict[str, Any]:
    creds_path = _resolve_credentials_file()
    try:
        config = json.loads(creds_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RuntimeError("Google credentials file is not valid JSON") from exc

    if not isinstance(config, dict):
        raise RuntimeError("Google credentials JSON must be an object")
    if "web" not in config and "installed" not in config:
        raise RuntimeError("Google credentials JSON must contain a 'web' client or 'installed' client")

    return config


def has_calendar_credentials(user_id: str) -> bool:
    return _user_token_file(user_id).exists()


def _token_missing_required_scopes(token_path: Path) -> bool:
    try:
        token_data = json.loads(token_path.read_text(encoding="utf-8"))
    except Exception:
        return False

    raw_scopes = token_data.get("scopes") or token_data.get("scope")
    if not raw_scopes:
        return False
    if isinstance(raw_scopes, str):
        granted_scopes = set(raw_scopes.split())
    elif isinstance(raw_scopes, list):
        granted_scopes = {str(scope) for scope in raw_scopes}
    else:
        return False

    return bool(set(GOOGLE_SCOPES) - granted_scopes)


def build_google_oauth_authorization_url(redirect_uri: str, state: str) -> str:
    _, _, Flow, _ = _require_google_calendar_deps()

    flow = Flow.from_client_config(_load_client_config(), scopes=GOOGLE_SCOPES, state=state)
    flow.redirect_uri = redirect_uri

    authorization_url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes=False,
        prompt="consent select_account",
    )
    return authorization_url


def exchange_google_oauth_code(user_id: str, code: str, redirect_uri: str) -> None:
    _, _, Flow, _ = _require_google_calendar_deps()

    os.environ.setdefault("OAUTHLIB_RELAX_TOKEN_SCOPE", "1")

    flow = Flow.from_client_config(_load_client_config(), scopes=GOOGLE_SCOPES)
    flow.redirect_uri = redirect_uri
    flow.fetch_token(code=code)

    token_path = _user_token_file(user_id)
    token_path.parent.mkdir(parents=True, exist_ok=True)
    token_path.write_text(flow.credentials.to_json(), encoding="utf-8")


def get_credentials(user_id: Optional[str] = None):
    """
    Load and refresh Google OAuth credentials for *user_id*.

    Raises RuntimeError with a clear message in two failure modes:
    - Token file does not exist  -> prompt OAuth start
    - invalid_grant on refresh   -> token revoked or app in Testing mode (7-day
      lifetime); stale file is deleted and user must re-authorise
    """
    Request, Credentials, _, _ = _require_google_calendar_deps()

    if user_id:
        token_path = _user_token_file(user_id)
    else:
        token_path = _legacy_token_file()

    creds = None
    if token_path.exists():
        if _token_missing_required_scopes(token_path):
            raise RuntimeError(
                "Google token is missing newly required scopes. Please reconnect Google from the app."
            )
        creds = Credentials.from_authorized_user_file(str(token_path), GOOGLE_SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as refresh_err:
                err_str = str(refresh_err).lower()
                if "invalid_grant" in err_str or "bad request" in err_str:
                    log.warning(
                        "Google refresh token invalid for user %s - deleting stale token file. "
                        "User must reconnect via OAuth.",
                        user_id,
                    )
                    try:
                        token_path.unlink(missing_ok=True)
                    except Exception:
                        pass
                    raise RuntimeError(
                        "Google Calendar session expired or was revoked. "
                        "Please reconnect your Google account via /calendar/oauth/start."
                    ) from refresh_err
                raise RuntimeError(f"Failed to refresh Google token: {refresh_err}") from refresh_err
        else:
            raise RuntimeError(
                "Google Calendar is not connected for this account. Start OAuth via /calendar/oauth/start."
            )

        token_path.parent.mkdir(parents=True, exist_ok=True)
        token_path.write_text(creds.to_json(), encoding="utf-8")

    return creds


def _get_user_email(user_id: Optional[str]) -> str:
    """
    Read the authenticated Google user's email from the stored token JSON.
    Returns empty string if unavailable (non-fatal - used only for Qdrant payload).
    """
    if not user_id:
        return ""
    try:
        token_path = _user_token_file(user_id)
        if not token_path.exists():
            return ""
        token_data = json.loads(token_path.read_text(encoding="utf-8"))
        return str(token_data.get("client_email") or token_data.get("email") or "")
    except Exception:
        return ""


def get_all_connected_user_ids() -> List[str]:
    """
    Return a list of all user_ids that have a valid Google Calendar token on disk.
    Used by the nightly scheduler to sync every connected user.
    """
    token_dir = _token_dir()
    if not token_dir.exists():
        return []
    user_ids: List[str] = []
    for token_file in token_dir.glob("*.json"):
        user_id = token_file.stem
        if user_id:
            user_ids.append(user_id)
    return user_ids


def get_calendar_service(user_id: Optional[str] = None):
    _, _, _, build = _require_google_calendar_deps()
    creds = get_credentials(user_id=user_id)
    return build("calendar", "v3", credentials=creds)
