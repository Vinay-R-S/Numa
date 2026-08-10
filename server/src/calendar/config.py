"""Calendar feature configuration (NUMA-114 P4, PLAN 2.2 / 5.1).

Env reads lifted out of `router.py` so the HTTP layer holds no configuration.
Values are resolved at import time, exactly as before.
"""
import os

WATCH_WEBHOOK_TOKEN = os.getenv("WATCH_WEBHOOK_TOKEN", "")
GOOGLE_WEBHOOK_BASE_URL = os.getenv("GOOGLE_WEBHOOK_BASE_URL", "")

JWT_SECRET = os.getenv("JWT_SECRET", "")
JWT_ALGORITHM = "HS256"

GOOGLE_OAUTH_REDIRECT_URI = os.getenv(
    "GOOGLE_OAUTH_REDIRECT_URI",
    "http://localhost:8000/calendar/oauth/callback",
)
GOOGLE_OAUTH_SUCCESS_REDIRECT = os.getenv(
    "GOOGLE_OAUTH_SUCCESS_REDIRECT",
    f"{os.getenv('FRONTEND_URL', 'http://localhost:3000').rstrip('/')}/calendar",
)
