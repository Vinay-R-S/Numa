"""
NUMA Smart Agent

Analyses incoming Slack messages to:
1. Detect relevance  — message mentions a NUMA user or is a @channel / @here broadcast
2. Extract tasks     — LLM decides if the message requires action and extracts task details
3. Create tasks      — inserts actionable items into Supabase automatically

Entry points
------------
is_relevant(text, slack_user_id)        -> bool
run_agent_for_message(text, ts, team_id) -> None   (resolves users + creates tasks)
"""
import logging
import re
from typing import Optional

from pydantic import BaseModel
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser

from app.config import settings
from app.database import get_supabase

logger = logging.getLogger(__name__)

# ── LLM output schema ─────────────────────────────────────────────────────────

class TaskExtraction(BaseModel):
    is_actionable: bool
    task_title: Optional[str] = None
    task_priority: str = "medium"   # low | medium | high | urgent
    task_due: Optional[str] = None  # ISO-8601 date (YYYY-MM-DD) or null

# ── LLM chain ─────────────────────────────────────────────────────────────────

_VALID_PRIORITIES = {"low", "medium", "high", "urgent"}

_parser = PydanticOutputParser(pydantic_object=TaskExtraction)

_prompt = ChatPromptTemplate.from_messages([
    ("system", """You are NUMA, a personal productivity assistant embedded in Slack.
Today's date is {today}.

Analyse the Slack message below and decide whether it contains an action item
that the receiver must act on.

Rules:
- is_actionable = true when the receiver needs to DO something — including:
    * Attend a meeting, standup, call, or sync
    * Review, approve, or respond to something
    * Complete a task or follow up on something
    * Show up somewhere at a specific time
- is_actionable = false for pure FYI messages with no required action, praise, or casual chat
- task_title: short, starts with an imperative verb (e.g. "Join standup", "Review PR #42", "Reply to Alice")
- task_priority: urgent=today/ASAP | high=this week | medium=general | low=FYI only
- task_due: ISO-8601 date (YYYY-MM-DD) calculated from today's date when a deadline is mentioned, otherwise null

{format_instructions}"""),
    ("human", "{text}"),
])

_llm = ChatGroq(
    model="llama-3.1-8b-instant",
    temperature=0,
    api_key=settings.GROQ_API_KEY,
)

_chain = _prompt | _llm | _parser

# ── Helpers ───────────────────────────────────────────────────────────────────

_MENTION_RE = re.compile(r"<@([A-Z0-9]+)>")


def is_relevant(text: str, slack_user_id: str) -> bool:
    """True when the message explicitly mentions the user or is a @channel / @here broadcast."""
    return (
        f"<@{slack_user_id}>" in text
        or "<!channel>" in text
        or "<!here>" in text
        or "<!everyone>" in text
    )


def _get_mentioned_slack_ids(text: str) -> list[str]:
    return _MENTION_RE.findall(text)


def _maybe_create_task(text: str, user_id: str, slack_ts: str | None) -> bool:
    """
    Ask the LLM whether *text* is actionable.
    If yes, insert a task for *user_id* and return True.
    """
    try:
        from datetime import date
        result: TaskExtraction = _chain.invoke({
            "text": text,
            "today": date.today().isoformat(),
            "format_instructions": _parser.get_format_instructions(),
        })
    except Exception as exc:
        logger.warning("Agent LLM call failed: %s", exc)
        return False

    if not result.is_actionable or not result.task_title:
        return False

    priority = result.task_priority if result.task_priority in _VALID_PRIORITIES else "medium"
    payload: dict = {
        "user_id": user_id,
        "title": result.task_title,
        "priority": priority,
        "status": "todo",
        "source": "ai",
        "slack_ts": slack_ts,
    }
    if result.task_due:
        payload["due_date"] = result.task_due

    try:
        get_supabase().table("tasks").insert(payload).execute()
        logger.info("Agent created task '%s' for user %s", result.task_title, user_id)
        return True
    except Exception as exc:
        logger.warning("Agent task insert failed: %s", exc)
        return False


# ── Public entry point ────────────────────────────────────────────────────────

def run_agent_for_message(text: str, ts: str | None, team_id: str | None = None) -> None:
    """
    Resolve every NUMA user who should be notified about this message, then
    run the task-extraction LLM for each of them.

    Notified users:
      - Any user whose Slack ID appears as <@USER_ID> in the text
      - All users in *team_id* when the message contains @channel / @here / @everyone
    """
    if not text:
        return

    db = get_supabase()
    users: list[dict] = []
    seen_ids: set[str] = set()

    # Direct mentions
    mentioned_slack_ids = _get_mentioned_slack_ids(text)
    if mentioned_slack_ids:
        resp = (
            db.table("users")
            .select("id,slack_user_id")
            .in_("slack_user_id", mentioned_slack_ids)
            .execute()
        )
        for u in (resp.data or []):
            if u["id"] not in seen_ids:
                users.append(u)
                seen_ids.add(u["id"])

    # Broadcast mentions — notify everyone in the team
    if ("<!channel>" in text or "<!here>" in text or "<!everyone>" in text) and team_id:
        resp = (
            db.table("users")
            .select("id,slack_user_id")
            .eq("slack_team_id", team_id)
            .execute()
        )
        for u in (resp.data or []):
            if u["id"] not in seen_ids:
                users.append(u)
                seen_ids.add(u["id"])

    logger.info("Agent processing message for %d user(s) | team_id=%s", len(users), team_id)

    for user in users:
        _maybe_create_task(text, user["id"], slack_ts=ts)
