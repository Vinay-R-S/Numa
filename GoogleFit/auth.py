"""
Authentication Module
Unified OAuth handling for Google Fit and Strava using environment variables.

Configuration via .env file:
- GOOGLE_FIT_CREDENTIALS_FILE: Path to Google OAuth credentials
- STRAVA_CLIENT_ID, STRAVA_CLIENT_SECRET: Strava app credentials
- STRAVA_ACCESS_TOKEN, STRAVA_REFRESH_TOKEN: Strava OAuth tokens
- STRAVA_TOKEN_EXPIRES_AT: Token expiration timestamp
"""

import os
import re
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

import requests
from dotenv import load_dotenv, set_key
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

# Load environment variables
ENV_PATH = Path(__file__).parent / '.env'
load_dotenv(ENV_PATH)

# ============================================================================
# CONFIGURATION FROM .env
# ============================================================================

# Google Fit
GOOGLE_SCOPES = [
    'https://www.googleapis.com/auth/fitness.activity.read',
    'https://www.googleapis.com/auth/fitness.sleep.read',
    'https://www.googleapis.com/auth/fitness.location.read',
]
GOOGLE_CREDENTIALS_FILE = os.getenv('GOOGLE_FIT_CREDENTIALS_FILE', 'credentials.json')
GOOGLE_TOKEN_FILE = 'token.json'

# Strava
STRAVA_CLIENT_ID = os.getenv('STRAVA_CLIENT_ID')
STRAVA_CLIENT_SECRET = os.getenv('STRAVA_CLIENT_SECRET')
STRAVA_AUTH_CODE = os.getenv('STRAVA_AUTH_CODE')
STRAVA_TOKEN_URL = 'https://www.strava.com/oauth/token'


# ============================================================================
# HELPER: UPDATE .env FILE
# ============================================================================

def update_env_variable(key: str, value: str):
    """
    Update a variable in the .env file.
    
    Writes the new value while preserving all other content and comments.
    """
    if not ENV_PATH.exists():
        return
    
    # Use python-dotenv's set_key for clean updates
    set_key(str(ENV_PATH), key, value)


def get_env_value(key: str, default: str = '') -> str:
    """Get environment variable value, refreshing from .env."""
    load_dotenv(ENV_PATH, override=True)
    return os.getenv(key, default)


# ============================================================================
# GOOGLE FIT AUTHENTICATION
# ============================================================================

def get_google_fit_service():
    """
    Create and return authenticated Google Fitness API service.
    
    Uses GOOGLE_FIT_CREDENTIALS_FILE from .env (defaults to credentials.json).
    Tokens are saved to token.json for reuse.
    
    Returns:
        Google Fitness API service instance
        
    Raises:
        FileNotFoundError: If credentials file is missing
    """
    creds = None
    
    # Check for existing tokens
    if os.path.exists(GOOGLE_TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(GOOGLE_TOKEN_FILE, GOOGLE_SCOPES)
    
    # Authenticate if needed
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(GOOGLE_CREDENTIALS_FILE):
                raise FileNotFoundError(
                    f"'{GOOGLE_CREDENTIALS_FILE}' not found. "
                    "Download OAuth credentials from Google Cloud Console."
                )
            
            flow = InstalledAppFlow.from_client_secrets_file(
                GOOGLE_CREDENTIALS_FILE, GOOGLE_SCOPES
            )
            creds = flow.run_local_server(port=0)
        
        # Save tokens
        with open(GOOGLE_TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())
    
    return build('fitness', 'v1', credentials=creds)


# ============================================================================
# STRAVA AUTHENTICATION
# ============================================================================

def is_strava_configured() -> bool:
    """Check if Strava credentials are configured in .env."""
    return bool(STRAVA_CLIENT_ID and STRAVA_CLIENT_SECRET)


def _parse_expiry(expiry_str: str) -> datetime:
    """Parse expiration time from .env (supports ISO format or Unix timestamp)."""
    if not expiry_str:
        return datetime.min
    
    expiry_str = expiry_str.strip()
    
    # Try Unix timestamp (integer)
    try:
        ts = int(expiry_str)
        return datetime.fromtimestamp(ts)
    except ValueError:
        pass
    
    # Try ISO format (2026-02-05T18:48:44Z)
    try:
        # Remove Z suffix if present
        if expiry_str.endswith('Z'):
            expiry_str = expiry_str[:-1]
        return datetime.fromisoformat(expiry_str)
    except ValueError:
        pass
    
    return datetime.min


def _is_token_expired() -> bool:
    """Check if Strava access token is expired."""
    expires_at = get_env_value('STRAVA_TOKEN_EXPIRES_AT')
    if not expires_at:
        return True
    
    expiry = _parse_expiry(expires_at)
    # Add 5 minute buffer
    return datetime.now() >= expiry


def _exchange_auth_code() -> Dict[str, Any]:
    """
    Exchange authorization code for access and refresh tokens.
    
    This is a one-time operation after user authorizes the app.
    The auth code can only be used once.
    """
    if not STRAVA_AUTH_CODE:
        raise ValueError("STRAVA_AUTH_CODE not set in .env")
    
    response = requests.post(STRAVA_TOKEN_URL, data={
        'client_id': STRAVA_CLIENT_ID,
        'client_secret': STRAVA_CLIENT_SECRET,
        'code': STRAVA_AUTH_CODE,
        'grant_type': 'authorization_code'
    })
    
    if response.status_code != 200:
        raise Exception(f"Failed to exchange auth code: {response.text}")
    
    return response.json()


def _refresh_strava_token() -> Dict[str, Any]:
    """
    Refresh expired access token using refresh token.
    
    Strava access tokens expire after 6 hours.
    Refresh tokens are long-lived and can be reused.
    """
    refresh_token = get_env_value('STRAVA_REFRESH_TOKEN')
    if not refresh_token:
        raise ValueError("STRAVA_REFRESH_TOKEN not set in .env")
    
    response = requests.post(STRAVA_TOKEN_URL, data={
        'client_id': STRAVA_CLIENT_ID,
        'client_secret': STRAVA_CLIENT_SECRET,
        'refresh_token': refresh_token,
        'grant_type': 'refresh_token'
    })
    
    if response.status_code != 200:
        raise Exception(f"Failed to refresh token: {response.text}")
    
    return response.json()


def _save_strava_tokens(tokens: Dict[str, Any]):
    """
    Save Strava tokens to .env file.
    
    Updates:
    - STRAVA_ACCESS_TOKEN
    - STRAVA_REFRESH_TOKEN
    - STRAVA_TOKEN_EXPIRES_AT (Unix timestamp)
    """
    if 'access_token' in tokens:
        update_env_variable('STRAVA_ACCESS_TOKEN', tokens['access_token'])
    
    if 'refresh_token' in tokens:
        update_env_variable('STRAVA_REFRESH_TOKEN', tokens['refresh_token'])
    
    if 'expires_at' in tokens:
        # Convert Unix timestamp to ISO format for readability
        expiry = datetime.fromtimestamp(tokens['expires_at'])
        update_env_variable('STRAVA_TOKEN_EXPIRES_AT', expiry.isoformat())


def get_strava_access_token() -> Optional[str]:
    """
    Get valid Strava access token.
    
    Token Flow:
    1. Check if access token exists and is valid
    2. If expired, refresh using refresh token
    3. If no tokens, exchange auth code (one-time)
    4. Save new tokens to .env
    
    Returns:
        Access token string, or None if not configured
    """
    if not is_strava_configured():
        return None
    
    # Check for existing access token
    access_token = get_env_value('STRAVA_ACCESS_TOKEN')
    
    if access_token and not _is_token_expired():
        # Token is valid, use it
        return access_token
    
    # Check for refresh token
    refresh_token = get_env_value('STRAVA_REFRESH_TOKEN')
    
    if refresh_token:
        # Refresh the access token
        try:
            tokens = _refresh_strava_token()
            _save_strava_tokens(tokens)
            return tokens['access_token']
        except Exception as e:
            print(f"Token refresh failed: {e}")
            # Fall through to try auth code
    
    # Try exchanging auth code (one-time)
    auth_code = get_env_value('STRAVA_AUTH_CODE')
    if auth_code:
        try:
            tokens = _exchange_auth_code()
            _save_strava_tokens(tokens)
            return tokens['access_token']
        except Exception as e:
            print(f"Auth code exchange failed: {e}")
            return None
    
    return None


def clear_strava_auth():
    """Clear Strava tokens from .env."""
    update_env_variable('STRAVA_ACCESS_TOKEN', '')
    update_env_variable('STRAVA_REFRESH_TOKEN', '')
    update_env_variable('STRAVA_TOKEN_EXPIRES_AT', '')


def clear_google_auth():
    """Clear Google tokens."""
    if os.path.exists(GOOGLE_TOKEN_FILE):
        os.remove(GOOGLE_TOKEN_FILE)


def get_strava_auth_url() -> str:
    """
    Get Strava authorization URL for manual auth.
    
    User should visit this URL, authorize, and copy the code from the redirect URL.
    """
    redirect_uri = os.getenv('REDIRECT_URI', 'http://localhost:8501')
    return (
        f"https://www.strava.com/oauth/authorize?"
        f"client_id={STRAVA_CLIENT_ID}&"
        f"redirect_uri={redirect_uri}&"
        f"response_type=code&"
        f"scope=activity:read_all"
    )
