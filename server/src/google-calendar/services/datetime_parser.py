"""
Deterministic Datetime Parser
Resolves natural date expressions using system clock only.
Never relies on LLM inference for date/time resolution.
"""

import os
from datetime import datetime, timedelta
import pytz

# IST timezone — forced, never converted
TIMEZONE_NAME = os.getenv('TIMEZONE', 'Asia/Kolkata')
IST = pytz.timezone(TIMEZONE_NAME)


def get_now_ist() -> datetime:
    """Return current datetime in IST from the system clock."""
    return datetime.now(IST)


def resolve_natural_date(text: str) -> datetime:
    """
    Resolve a natural date expression to a timezone-aware IST datetime.
    
    Supports ONLY deterministic expressions:
      - "today"    → today's date at 00:00 IST
      - "tomorrow" → tomorrow's date at 00:00 IST
      - "tmr"      → alias for tomorrow
    
    Args:
        text: Natural date expression (case-insensitive)
    
    Returns:
        datetime: Timezone-aware datetime in Asia/Kolkata
    
    Raises:
        ValueError: If the expression is not supported
    """
    cleaned = text.strip().lower()
    now = get_now_ist()
    
    if cleaned == "today":
        base = now.replace(hour=0, minute=0, second=0, microsecond=0)
        return IST.localize(base.replace(tzinfo=None))
    
    if cleaned in ("tomorrow", "tmr"):
        base = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        return IST.localize(base.replace(tzinfo=None))
    
    raise ValueError(
        f"Unsupported natural date expression: '{text}'. "
        f"Supported values: 'today', 'tomorrow', 'tmr'. "
        f"For specific dates, use ISO 8601 format (e.g. 2026-02-13T19:00:00)."
    )
