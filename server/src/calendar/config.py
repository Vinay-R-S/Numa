"""Calendar feature configuration (NUMA-114 P4, PLAN 2.2 / 5.1).

Env reads lifted out of `router.py` so the HTTP layer holds no configuration.
Values are resolved at import time, exactly as before.
"""
import os

WEBHOOK_TOKEN_ENV = "WATCH_WEBHOOK_TOKEN"

#: Shared secret Google echoes back as X-Goog-Channel-Token. Optional: when it is
#: unset each watch registers a per-process token instead (NUMA-131). Set it in
#: production so notifications survive a restart and match across workers.
WATCH_WEBHOOK_TOKEN = os.getenv(WEBHOOK_TOKEN_ENV, "")
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
