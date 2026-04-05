"""
Message analyzer — categorises Slack messages into mentions / meetings / urgent / general.
"""
from typing import List, Dict, Any

MEETING_KEYWORDS  = {"meeting", "standup", "sync", "call", "zoom", "teams"}
URGENT_KEYWORDS   = {"urgent", "deadline", "asap", "critical", "blocker", "production"}
GENERAL_KEYWORDS  = {"reminder", "tomorrow", "fyi", "heads up", "note"}


def analyze_messages(
    messages: List[Dict[str, Any]],
    user_id: str | None = None,
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Categorise messages.

    Returns a dict with keys: mentions, meetings, urgent, general.
    A message can appear in more than one category (e.g. an urgent mention).
    """
    result: Dict[str, List[Dict[str, Any]]] = {
        "mentions": [],
        "meetings": [],
        "urgent":   [],
        "general":  [],
    }

    mention_tag = f"<@{user_id}>" if user_id else None

    for msg in messages:
        text = msg.get("text", "")
        if not text:
            continue

        text_lower = text.lower()
        categorised = False

        # 1. Direct mention
        if mention_tag and mention_tag in text:
            result["mentions"].append(msg)
            categorised = True

        # 2. Meeting-related
        if any(kw in text_lower for kw in MEETING_KEYWORDS):
            result["meetings"].append(msg)
            categorised = True

        # 3. Urgent / high-priority
        if any(kw in text_lower for kw in URGENT_KEYWORDS):
            result["urgent"].append(msg)
            categorised = True

        # 4. General interest (only if not already categorised)
        if not categorised and any(kw in text_lower for kw in GENERAL_KEYWORDS):
            result["general"].append(msg)

    return result
