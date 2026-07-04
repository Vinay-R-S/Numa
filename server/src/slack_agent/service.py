"""
Slack Sub-Agent Service
=======================
LangGraph agentic loop that handles Slack-related queries routed from
the Master Agent.

Tools available to the LLM
---------------------------
search_slack_messages   - semantic search over Qdrant
get_recent_messages     - PostgreSQL fetch (last N rows)
send_slack_message      - Slack Web API post
create_slack_channel    - Slack Web API channel creation
invite_user_to_channel  - invite a Slack user to a channel
create_task_from_slack  - insert into public.tasks (source_name='Slack')
list_slack_tasks        - list tasks where source_name='Slack'

Entry point
-----------
run_slack_agent_chat(query, history, user_id, model=None) -> Dict
"""
from __future__ import annotations

import importlib
import hashlib
import json
import logging
import os
import re
from datetime import datetime, timedelta, timezone
from typing import Annotated, Dict, List, Optional, Sequence, Tuple, TypedDict

import httpx
import operator

log = logging.getLogger(__name__)

SLACK_AGENT_SYSTEM_PROMPT = (
    "You are NUMA Slack sub-agent. You help users interact with their Slack workspace. "
    "You can search recent Slack messages, send messages to channels, and create tasks from Slack content. "
    "You can create Slack channels and invite teammates when asked. "
    "Always use tools to fetch real data - never fabricate messages or channel names. "
    "When creating a task from Slack, base it on an actual recent Slack message and include slack_ts when available. "
    "Do not invent placeholder tasks like Review PR #42 unless that exact content exists in Slack. "
    "If Slack credentials are not configured, inform the user politely and guide them to Settings → Connect Slack. "
    "Do not use emojis. Keep responses concise and action-oriented. Use plain Markdown when structure helps."
)


# ── LangGraph state ───────────────────────────────────────────────────────────

class SlackAgentState(TypedDict):
    messages: Annotated[Sequence[object], operator.add]
    user_query: str
    user_id: str
    semantic_context: str
    mutated: bool


# ── Dependency loader ─────────────────────────────────────────────────────────

def _require_deps() -> Dict:
    try:
        msgs_mod  = importlib.import_module("langchain_core.messages")
        tools_mod = importlib.import_module("langchain_core.tools")
        graph_mod = importlib.import_module("langgraph.graph")

        return {
            "AIMessage":    getattr(msgs_mod,  "AIMessage"),
            "HumanMessage": getattr(msgs_mod,  "HumanMessage"),
            "SystemMessage": getattr(msgs_mod, "SystemMessage"),
            "ToolMessage":  getattr(msgs_mod,  "ToolMessage"),
            "tool":         getattr(tools_mod, "tool"),
            "StateGraph":   getattr(graph_mod, "StateGraph"),
            "END":          getattr(graph_mod, "END"),
        }
    except Exception as exc:
        raise RuntimeError(f"Slack agent dependencies missing: {exc}") from exc


def _get_llm(model_override=None, user_id=None):
    from ..llm_factory import get_llm_with_fallback
    return get_llm_with_fallback(
        user_id=user_id,
        agent_name="slack",
        priority="normal",
        model=model_override,
    )


# ── PostgreSQL helpers ────────────────────────────────────────────────────────

from .repository import slack_repository


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def _clean_slack_text(text: str) -> str:
    cleaned = re.sub(r"<@([A-Z0-9]+)>", "", text or "")
    cleaned = re.sub(r"<#[A-Z0-9]+\|([^>]+)>", r"#\1", cleaned)
    cleaned = re.sub(r"<![^>]+>", "", cleaned)
    return _normalize_text(cleaned)


def _parse_slack_due(text: str) -> Optional[datetime]:
    lower = text.lower()
    day_offset: Optional[int] = None
    if re.search(r"\b(tom|tmr|tomorrow)\b", lower):
        day_offset = 1
    elif re.search(r"\b(today|tonight)\b", lower):
        day_offset = 0

    if day_offset is None and not re.search(r"\b(by|before|due)\b", lower):
        return None

    time_match = re.search(r"\b(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\b", lower)
    if not time_match:
        return None

    hour = int(time_match.group(1))
    minute = int(time_match.group(2) or "0")
    meridiem = time_match.group(3)
    if meridiem == "pm" and hour < 12:
        hour += 12
    elif meridiem == "am" and hour == 12:
        hour = 0

    if hour > 23 or minute > 59:
        return None

    due_date = (datetime.now(timezone.utc) + timedelta(days=day_offset or 0)).date()
    return datetime.combine(due_date, datetime.min.time(), tzinfo=timezone.utc).replace(
        hour=hour,
        minute=minute,
    )


def _strip_due_clause(text: str) -> str:
    return _normalize_text(re.sub(r"\b(by|before|due)\b\s+.*$", "", text, flags=re.IGNORECASE))


def _slack_task_priority(text: str) -> str:
    lower = text.lower()
    if any(word in lower for word in ("urgent", "asap", "immediately", "critical")):
        return "urgent"
    if any(word in lower for word in ("important", "high priority", "deadline")):
        return "high"
    if any(word in lower for word in ("whenever", "low priority")):
        return "low"
    return "medium"


def _slack_task_title(text: str) -> Optional[str]:
    cleaned = _strip_due_clause(_clean_slack_text(text))
    cleaned = re.sub(r"^(hi|hii|hello|hey)\s+", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"^(pls|please)\s+", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(
        r"^(can\s+u|can\s+you|could\s+you|would\s+you)\s+",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(
        r"^(pls|please)\s+(can\s+u|can\s+you|could\s+you|would\s+you)\s+",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = _normalize_text(cleaned)
    if not cleaned:
        return None

    first_word = cleaned.split(" ", 1)[0].lower()
    actionable_verbs = {
        "send",
        "share",
        "review",
        "fix",
        "update",
        "create",
        "complete",
        "finish",
        "prepare",
        "check",
        "upload",
        "write",
    }
    if first_word not in actionable_verbs and not re.search(r"\b(pls|please|can u|can you|by|due)\b", text, re.I):
        return None

    return cleaned[:1].upper() + cleaned[1:]


def _is_actionable_slack_message(text: str) -> bool:
    lower = text.lower()
    if "has joined the channel" in lower:
        return False
    if len(_clean_slack_text(text)) < 8:
        return False
    return bool(
        re.search(
            r"\b(pls|please|can u|can you|could you|would you|send|share|review|fix|update|create|complete|finish|prepare|check|upload|write|by|due)\b",
            lower,
        )
    )


def _fetch_recent_db_messages(user_id: str, limit: int = 15, channel_name: Optional[str] = None) -> List[Dict]:
    """Fetch recent Slack messages for a user from PostgreSQL (7-day window)."""
    try:
        return slack_repository.recent_messages(user_id, limit, channel_name)
    except Exception as exc:
        log.warning("_fetch_recent_db_messages failed: %s", exc)
        return []


def _insert_task_from_slack(
    user_id: str,
    title: str,
    priority: str = "medium",
    due_date: Optional[str | datetime] = None,
    slack_ts: Optional[str] = None,
    description: Optional[str] = None,
    status: str = "planned",
) -> Optional[Dict]:
    """Insert a task into public.tasks with source_name='Slack'."""
    due = None
    if due_date:
        try:
            due = due_date if isinstance(due_date, datetime) else datetime.fromisoformat(str(due_date).replace("Z", "+00:00"))
        except Exception:
            pass

    normalized_title = _normalize_text(title)
    if not normalized_title:
        return None

    if priority not in {"low", "medium", "high", "urgent"}:
        priority = "medium"
    if status not in {"planned", "inprogress", "completed", "pending"}:
        status = "planned"

    if slack_ts:
        ext = f"slack:{slack_ts}"
    else:
        raw_key = f"{user_id}|{normalized_title.lower()}|{_normalize_text(description or '').lower()}|{due.isoformat() if due else ''}"
        ext = f"slack:manual:{hashlib.sha256(raw_key.encode('utf-8')).hexdigest()[:24]}"

    completed_at = datetime.now(timezone.utc) if status == "completed" else None
    try:
        task = slack_repository.insert_task_from_slack(
            user_id, normalized_title, description, status, priority, due, ext, completed_at,
        )
    except Exception as exc:
        log.warning("_insert_task_from_slack failed: %s", exc)
        return None

    if task:
        try:
            from ..tasks import service as task_service
            task_service.store_task_snapshot(task)
        except Exception:
            pass
    return task


def _list_slack_tasks(user_id: str, limit: int = 10) -> List[Dict]:
    """List tasks created from Slack for a user."""
    try:
        return slack_repository.list_slack_tasks(user_id, limit)
    except Exception as exc:
        log.warning("_list_slack_tasks failed: %s", exc)
        return []


# ── Slack SDK helper ──────────────────────────────────────────────────────────

def _find_recent_message_for_task(user_id: str, title: str) -> Optional[Dict]:
    title_words = {
        word
        for word in re.findall(r"[a-z0-9]+", title.lower())
        if len(word) > 2
    }
    if not title_words:
        return None

    for message in _fetch_recent_db_messages(user_id=user_id, limit=30):
        text_words = set(re.findall(r"[a-z0-9]+", (message.get("text") or "").lower()))
        if title_words.issubset(text_words):
            return message
    return None


def _create_tasks_from_recent_slack(user_id: str, limit: int = 20) -> Tuple[List[Dict], int]:
    created: List[Dict] = []
    inspected = 0

    for message in reversed(_fetch_recent_db_messages(user_id=user_id, limit=limit)):
        text = message.get("text") or ""
        inspected += 1
        if not _is_actionable_slack_message(text):
            continue

        title = _slack_task_title(text)
        if not title:
            continue

        description = (
            f"Slack #{message.get('channel_name') or message.get('slack_channel_id')}\n"
            f"Original message: {text}"
        )
        task = _insert_task_from_slack(
            user_id=user_id,
            title=title,
            priority=_slack_task_priority(text),
            due_date=_parse_slack_due(text),
            slack_ts=str(message.get("ts") or ""),
            description=description,
        )
        if task:
            created.append(task)

    return created, inspected


def _get_slack_token_for_user(user_id: str) -> Optional[str]:
    try:
        row = slack_repository.slack_tokens_for_user(user_id)
        row_token = "" if not row else (row[0] or row[1] or "").strip()
        if row_token:
            return row_token
    except Exception as exc:
        log.warning("_get_slack_token_for_user failed: %s", exc)

    env_token = os.getenv("SLACK_BOT_TOKEN", "").strip()
    if env_token and not env_token.startswith("xoxb-placeholder"):
        return env_token
    return None


def _slack_headers(token: str) -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json; charset=utf-8",
    }


def _resolve_channel_id(token: str, channel_name_or_id: str) -> Optional[str]:
    channel = channel_name_or_id.strip()
    if not channel:
        return None
    if re.match(r"^[CGD][A-Z0-9]+$", channel):
        return channel

    name = channel.lstrip("#").lower()
    cursor = ""
    with httpx.Client(timeout=15.0) as client:
        while True:
            resp = client.get(
                "https://slack.com/api/conversations.list",
                headers=_slack_headers(token),
                params={
                    "types": "public_channel,private_channel",
                    "exclude_archived": "true",
                    "limit": "500",
                    **({"cursor": cursor} if cursor else {}),
                },
            )
            data = resp.json()
            if not data.get("ok"):
                return None
            for item in data.get("channels", []):
                if str(item.get("name") or "").lower() == name:
                    return item.get("id")
            cursor = (data.get("response_metadata") or {}).get("next_cursor") or ""
            if not cursor:
                return None


def _send_slack_message_api(user_id: str, channel: str, text: str) -> Tuple[bool, str]:
    token = _get_slack_token_for_user(user_id)
    if not token:
        return False, "Slack is not connected. Connect Slack from Settings first."

    channel_id = _resolve_channel_id(token, channel)
    if not channel_id:
        return False, f"Channel #{channel.lstrip('#')} not found."

    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.post(
                "https://slack.com/api/chat.postMessage",
                headers=_slack_headers(token),
                json={"channel": channel_id, "text": text},
            )
        data = resp.json()
        if not data.get("ok"):
            return False, f"Slack API error: {data.get('error', 'unknown_error')}"
        return True, f"Message sent to #{channel.lstrip('#')}"
    except Exception as exc:
        return False, str(exc)


def _create_slack_channel_api(user_id: str, name: str, is_private: bool = False) -> Tuple[bool, str]:
    token = _get_slack_token_for_user(user_id)
    if not token:
        return False, "Slack is not connected. Connect Slack from Settings first."

    channel_name = re.sub(r"[^a-z0-9_-]+", "-", name.strip().lower()).strip("-")
    if not channel_name:
        return False, "Channel name is required."

    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.post(
                "https://slack.com/api/conversations.create",
                headers=_slack_headers(token),
                json={"name": channel_name, "is_private": is_private},
            )
        data = resp.json()
        if data.get("ok"):
            channel = data.get("channel") or {}
            return True, f"Created Slack channel #{channel.get('name') or channel_name}."

        error = data.get("error", "unknown_error")
        if error == "name_taken":
            return True, f"Slack channel #{channel_name} already exists."
        if error in {"missing_scope", "not_allowed_token_type"}:
            return False, "Slack token is missing channel creation scope. Reconnect Slack after adding channels:manage."
        return False, f"Slack API error: {error}"
    except Exception as exc:
        return False, str(exc)


def _resolve_slack_user_id(token: str, teammate: str) -> Optional[str]:
    target = teammate.strip()
    if not target:
        return None
    if re.match(r"^U[A-Z0-9]+$", target):
        return target

    normalized = target.lstrip("@").lower()
    cursor = ""
    with httpx.Client(timeout=15.0) as client:
        while True:
            resp = client.get(
                "https://slack.com/api/users.list",
                headers=_slack_headers(token),
                params={"limit": "500", **({"cursor": cursor} if cursor else {})},
            )
            data = resp.json()
            if not data.get("ok"):
                return None

            for member in data.get("members", []):
                if not isinstance(member, dict) or member.get("deleted") or member.get("is_bot"):
                    continue
                profile = member.get("profile") if isinstance(member.get("profile"), dict) else {}
                candidates = [
                    member.get("id"),
                    member.get("name"),
                    member.get("real_name"),
                    profile.get("display_name"),
                    profile.get("real_name"),
                    profile.get("email"),
                ]
                if any(str(value or "").strip().lower() == normalized for value in candidates):
                    return str(member.get("id"))

            cursor = (data.get("response_metadata") or {}).get("next_cursor") or ""
            if not cursor:
                return None


def _invite_user_to_slack_channel_api(user_id: str, channel: str, teammate: str) -> Tuple[bool, str]:
    token = _get_slack_token_for_user(user_id)
    if not token:
        return False, "Slack is not connected. Connect Slack from Settings first."

    channel_id = _resolve_channel_id(token, channel)
    if not channel_id:
        return False, f"Channel #{channel.lstrip('#')} not found."

    slack_user_id = _resolve_slack_user_id(token, teammate)
    if not slack_user_id:
        return False, (
            f"Could not find Slack user '{teammate}'. Use their Slack email, display name, or member ID."
        )

    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.post(
                "https://slack.com/api/conversations.invite",
                headers=_slack_headers(token),
                json={"channel": channel_id, "users": slack_user_id},
            )
        data = resp.json()
        if data.get("ok"):
            return True, f"Invited {teammate} to #{channel.lstrip('#')}."

        error = data.get("error", "unknown_error")
        if error == "already_in_channel":
            return True, f"{teammate} is already in #{channel.lstrip('#')}."
        if error in {"missing_scope", "not_allowed_token_type"}:
            return False, (
                "Slack token is missing invite permission. Reconnect Slack after adding channels:write.invites."
            )
        return False, f"Slack API error: {error}"
    except Exception as exc:
        return False, str(exc)


def _create_slack_channel_and_invite_api(
    user_id: str,
    name: str,
    teammate: str,
    is_private: bool = False,
) -> Tuple[bool, str]:
    created_ok, created_detail = _create_slack_channel_api(user_id, name, is_private)
    if not created_ok:
        return False, created_detail

    invite_ok, invite_detail = _invite_user_to_slack_channel_api(user_id, name, teammate)
    if not invite_ok:
        return False, f"{created_detail} But invite failed: {invite_detail}"
    return True, f"{created_detail} {invite_detail}"


# ── Tool factory ──────────────────────────────────────────────────────────────

def _parse_invite_command(query: str) -> Optional[Tuple[str, str]]:
    text = _normalize_text(query)
    patterns = [
        r"\b(?:add|invite)\s+(?P<teammate>[\w.+%-]+@[\w.-]+\.[A-Za-z]{2,}|<@?[A-Z0-9]+>|@?[\w.-]+)\s+(?:to|into)\s+(?:the\s+)?(?:channel\s+)?#?(?P<channel>[A-Za-z0-9_-]+)\b",
        r"\b(?:add|invite)\s+(?P<teammate>[\w.+%-]+@[\w.-]+\.[A-Za-z]{2,}|<@?[A-Z0-9]+>|@?[\w.-]+)\s+(?:to|into)\s+#(?P<channel>[A-Za-z0-9_-]+)\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            teammate = match.group("teammate").strip("<>@ ")
            channel = match.group("channel").strip("# ")
            if teammate and channel:
                return teammate, channel
    return None


def _parse_create_channel_command(query: str) -> Optional[str]:
    text = _normalize_text(query)
    match = re.search(
        r"\b(?:create|make)\s+(?:a\s+)?(?:new\s+)?(?:slack\s+)?channel(?:\s+(?:called|named))?\s+#?(?P<channel>[A-Za-z0-9_-]+)\b",
        text,
        flags=re.IGNORECASE,
    )
    if not match:
        return None
    channel = match.group("channel").strip("# ")
    return channel or None


def _slack_toolset(tool_decorator, user_id: str):
    def _coerce_limit(value, default: int = 10, maximum: int = 30) -> int:
        try:
            return max(1, min(int(value), maximum))
        except Exception:
            return default

    @tool_decorator
    def search_slack_messages(query: str, limit: int | str = 8) -> str:
        """Semantic search over the user's recent Slack messages stored in Qdrant.
        Use this to answer questions like 'what was discussed in #general?' or
        'find Slack messages about the release deadline'."""
        try:
            from .qdrant_store import search_messages  # type: ignore
            results = search_messages(user_id=user_id, query=query, limit=_coerce_limit(limit, 8, 20))
            if not results:
                return "No relevant Slack messages found."
            lines = [f"[{r['channel_name'] or 'unknown'}] {r['text'][:200]} ({r['created_at'][:10]})"
                     for r in results]
            return "Relevant Slack messages:\n" + "\n".join(lines)
        except Exception as exc:
            return f"Search error: {exc}"

    @tool_decorator
    def get_recent_messages(channel: str = "", limit: int | str = 10) -> str:
        """Fetch the most recent Slack messages (up to 7 days old).
        Optionally filter by channel name (without #).
        Use this when the user asks to 'show messages from #standup' or 'what's new in Slack'."""
        try:
            safe_limit = _coerce_limit(limit, 10, 30)
            msgs = _fetch_recent_db_messages(
                user_id=user_id,
                limit=safe_limit,
                channel_name=channel.lstrip("#") if channel else None,
            )
            if not msgs:
                return "No recent Slack messages found (last 7 days)."
            lines = [
                f"[{m['channel_name'] or m['slack_channel_id']}] {m['text'] or '(empty)'} "
                f"- {str(m['created_at'])[:16]}"
                for m in msgs
            ]
            return f"Recent messages ({len(lines)}):\n" + "\n".join(lines)
        except Exception as exc:
            return f"Error fetching messages: {exc}"

    @tool_decorator
    def send_slack_message(channel: str, text: str) -> str:
        """Send a message to a Slack channel.
        channel: channel name without # (e.g. 'general').
        text: the message content to post."""
        if not channel or not text:
            return "Both channel and text are required."
        ok, detail = _send_slack_message_api(user_id, channel, text)
        return detail

    @tool_decorator
    def create_slack_channel(name: str, is_private: bool = False) -> str:
        """Create a Slack channel.
        name: channel name, e.g. Coders. Slack will normalize this to lowercase.
        is_private: false for public channels, true for private channels."""
        if not name.strip():
            return "Channel name is required."
        ok, detail = _create_slack_channel_api(user_id, name, is_private)
        return detail

    @tool_decorator
    def invite_user_to_channel(channel: str, teammate: str) -> str:
        """Invite a teammate to an existing Slack channel.
        channel: channel name or ID.
        teammate: Slack email, display name, username, or member ID."""
        if not channel.strip() or not teammate.strip():
            return "Both channel and teammate are required."
        ok, detail = _invite_user_to_slack_channel_api(user_id, channel, teammate)
        return detail

    @tool_decorator
    def create_slack_channel_and_invite(
        name: str,
        teammate: str,
        is_private: bool = False,
    ) -> str:
        """Create a Slack channel and invite a teammate in one operation.
        name: channel name, e.g. Coders.
        teammate: Slack email, display name, username, or member ID.
        is_private: false for public channels, true for private channels."""
        if not name.strip() or not teammate.strip():
            return "Both channel name and teammate are required."
        ok, detail = _create_slack_channel_and_invite_api(user_id, name, teammate, is_private)
        return detail

    @tool_decorator
    def create_task_from_slack(
        title: str,
        priority: str = "medium",
        due_date: str = "",
        slack_ts: str = "",
        description: str = "",
    ) -> str:
        """Create a task in NUMA from a Slack message or discussion.
        title: short task description (imperative verb, e.g. 'Review PR #42').
        priority: low | medium | high | urgent.
        due_date: ISO-8601 date (YYYY-MM-DD) or empty.
        slack_ts: Slack message timestamp for deduplication (optional)."""
        if not title.strip():
            return "Task title is required."
        valid_priorities = {"low", "medium", "high", "urgent"}
        pri = priority.strip().lower() if priority.strip().lower() in valid_priorities else "medium"
        source_message = None
        if not slack_ts.strip():
            source_message = _find_recent_message_for_task(user_id, title)
            if not source_message:
                return (
                    "I could not find a recent Slack message matching that task. "
                    "Ask me to create tasks from recent Slack messages, or include the exact message."
                )
            slack_ts = str(source_message.get("ts") or "")
            if not description.strip():
                description = (
                    f"Slack #{source_message.get('channel_name') or source_message.get('slack_channel_id')}\n"
                    f"Original message: {source_message.get('text') or ''}"
                )
        task = _insert_task_from_slack(
            user_id=user_id,
            title=title.strip(),
            priority=pri,
            due_date=due_date.strip() or None,
            slack_ts=slack_ts.strip() or None,
            description=description.strip() or None,
        )
        if task:
            return f"Task created: \"{task.get('title')}\" [{task.get('priority')}] (id={task.get('id')})"
        return "Failed to create task. Please try again."

    @tool_decorator
    def list_slack_tasks(limit: int | str = 10) -> str:
        """List tasks in NUMA that were created from Slack messages."""
        tasks = _list_slack_tasks(user_id=user_id, limit=_coerce_limit(limit, 10, 30))
        if not tasks:
            return "No Slack-sourced tasks found."
        lines = [
            f"- {t['title']} [{t['status']} / {t['priority']}]"
            + (f" due {t['due_date']}" if t.get("due_date") else "")
            for t in tasks
        ]
        return f"Slack tasks ({len(lines)}):\n" + "\n".join(lines)

    return [
        search_slack_messages,
        get_recent_messages,
        send_slack_message,
        create_slack_channel,
        invite_user_to_channel,
        create_slack_channel_and_invite,
        create_task_from_slack,
        list_slack_tasks,
    ]


# ── LangGraph build ───────────────────────────────────────────────────────────

from functools import lru_cache

@lru_cache(maxsize=64)
def _build_slack_graph(user_id: str, model_override: Optional[str] = None):
    deps = _require_deps()

    AIMessage    = deps["AIMessage"]
    SystemMessage = deps["SystemMessage"]
    ToolMessage  = deps["ToolMessage"]
    StateGraph   = deps["StateGraph"]
    END          = deps["END"]

    tools    = _slack_toolset(deps["tool"], user_id)
    tool_map = {t.name: t for t in tools}
    mutation_tools = {
        "create_task_from_slack",
        "send_slack_message",
        "create_slack_channel",
        "invite_user_to_channel",
        "create_slack_channel_and_invite",
    }

    def call_model(state: SlackAgentState) -> SlackAgentState:
        llm = _get_llm(model_override=model_override, user_id=user_id)
        llm_with_tools = llm.bind_tools(tools)

        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        sem = (state.get("semantic_context") or "").strip()
        context_block = f"\nRelevant context from memory:\n{sem}\n" if sem else ""

        system = (
            f"{SLACK_AGENT_SYSTEM_PROMPT}\n"
            f"Current time: {now}"
            f"{context_block}"
        )
        full_messages = [SystemMessage(content=system)] + list(state["messages"])
        response = llm_with_tools.invoke(full_messages)
        return {
            "messages":         [response],
            "user_query":       state["user_query"],
            "user_id":          state["user_id"],
            "semantic_context": state["semantic_context"],
            "mutated":          state["mutated"],
        }

    def call_tools(state: SlackAgentState) -> SlackAgentState:
        last   = state["messages"][-1]
        out    = []
        mutated = state["mutated"]
        for tc in getattr(last, "tool_calls", []):
            name     = tc.get("name")
            args     = tc.get("args", {})
            tool_id  = tc.get("id")
            if name not in tool_map:
                result = f"Unknown tool '{name}'."
            else:
                try:
                    result = tool_map[name].invoke(args)
                    if name in mutation_tools and not str(result).lower().startswith("error"):
                        mutated = True
                except Exception as exc:
                    result = f"Error running {name}: {exc}"
            out.append(ToolMessage(content=str(result), tool_call_id=tool_id))
        return {
            "messages":         out,
            "user_query":       state["user_query"],
            "user_id":          state["user_id"],
            "semantic_context": state["semantic_context"],
            "mutated":          mutated,
        }

    def should_continue(state: SlackAgentState):
        last = state["messages"][-1]
        rounds = sum(
            1 for m in state["messages"]
            if hasattr(m, "tool_calls") and m.tool_calls
        )
        if rounds >= 6:
            return "end"
        if hasattr(last, "tool_calls") and last.tool_calls:
            return "call_tools"
        return "end"

    wf = StateGraph(SlackAgentState)
    wf.add_node("call_model", call_model)
    wf.add_node("call_tools", call_tools)
    wf.set_entry_point("call_model")
    wf.add_conditional_edges("call_model", should_continue, {"call_tools": "call_tools", "end": END})
    wf.add_edge("call_tools", "call_model")
    return wf.compile(), AIMessage


# ── Public entry point ────────────────────────────────────────────────────────

def run_slack_agent_chat(
    query: str,
    history: List[dict],
    user_id: Optional[str],
    model: Optional[str] = None,
    preloaded_context: Optional[str] = None,
) -> Dict:
    """Invoke the Slack sub-agent and return a response dict.

    Returns
    -------
    {
        "response":      str,
        "success":       bool,
        "delegated_to":  "slack-subagent",
        "refresh_slack": bool,
    }
    """
    if not user_id:
        return {
            "response":      "User session is missing. Please sign in again.",
            "success":       False,
            "delegated_to":  "slack-subagent",
            "refresh_slack": False,
        }

    normalized_query = re.sub(r"\s+", " ", query.lower()).strip()
    invite_args = _parse_invite_command(query)
    if invite_args:
        teammate, channel = invite_args
        ok, detail = _invite_user_to_slack_channel_api(user_id, channel, teammate)
        return {
            "response": detail,
            "success": ok,
            "delegated_to": "slack-subagent",
            "refresh_slack": ok,
        }

    channel_to_create = _parse_create_channel_command(query)
    if channel_to_create:
        ok, detail = _create_slack_channel_api(user_id, channel_to_create)
        return {
            "response": detail,
            "success": ok,
            "delegated_to": "slack-subagent",
            "refresh_slack": ok,
        }

    if re.search(r"\b(create|make|add)\b\s+(a\s+)?tasks?\s+from\s+slack\b", normalized_query):
        tasks, inspected = _create_tasks_from_recent_slack(user_id)
        if tasks:
            lines = [
                f"- {task.get('title')} [{task.get('priority') or 'medium'}]"
                + (f" due {task.get('due_date')}" if task.get("due_date") else "")
                for task in tasks
            ]
            return {
                "response": "Created Slack task(s):\n" + "\n".join(lines),
                "success": True,
                "delegated_to": "slack-subagent",
                "refresh_slack": True,
            }
        return {
            "response": (
                f"I inspected {inspected} recent Slack messages and did not find an actionable task. "
                "Ask with a specific message, or sync Slack and try again."
            ),
            "success": True,
            "delegated_to": "slack-subagent",
            "refresh_slack": False,
        }

    from ..llm_factory import is_any_llm_configured
    if not is_any_llm_configured(user_id):
        return {
            "response": (
                "Slack sub-agent is unavailable - no LLM provider is configured. "
                "Go to Settings and add an API key for your preferred AI provider."
            ),
            "success":       True,
            "delegated_to":  "slack-subagent",
            "refresh_slack": False,
        }

    try:
        deps          = _require_deps()
        HumanMessage  = deps["HumanMessage"]
        AIMessage     = deps["AIMessage"]

        # Use pre-loaded context from master agent, or build fresh
        if preloaded_context:
            semantic_context = preloaded_context
        else:
            try:
                from ..memory.service import memory_service  # type: ignore
                semantic_context = memory_service.build_context_for_query(user_id, query)
            except Exception:
                semantic_context = ""

        graph, AIMsg = _build_slack_graph(user_id, model)

        # Convert history
        history_messages: List[object] = []
        for m in history:
            content = (m.get("content") or "").strip()
            if not content:
                continue
            role = (m.get("role") or "").lower()
            if role == "user":
                history_messages.append(HumanMessage(content=content))
            elif role in ("assistant", "ai"):
                history_messages.append(AIMessage(content=content))

        initial_state: SlackAgentState = {
            "messages":         history_messages + [HumanMessage(content=query)],
            "user_query":       query,
            "user_id":          user_id,
            "semantic_context": semantic_context,
            "mutated":          False,
        }

        result    = graph.invoke(initial_state)
        messages  = result.get("messages", [])
        if not messages:
            raise RuntimeError("No response produced by Slack sub-agent")

        final   = messages[-1]
        content = getattr(final, "content", str(final))
        if isinstance(content, list):
            content = "\n".join(str(part) for part in content)

        mutated = bool(result.get("mutated", False))

        # Store in shared semantic memory
        if user_id and str(content).strip():
            try:
                from ..memory.service import memory_service  # type: ignore
                memory_service.store_turn(user_id, query, str(content))
            except Exception:
                pass

        return {
            "response":      str(content),
            "success":       True,
            "delegated_to":  "slack-subagent",
            "refresh_slack": mutated,
        }

    except Exception as exc:
        err = str(exc)
        err_lower = err.lower()
        if "winerror 10061" in err_lower or "connection refused" in err_lower:
            log.warning("Slack sub-agent LLM connection failed: %s", exc)
            response = (
                "Slack sub-agent could not reach the configured local Ollama server. "
                "Start Ollama, or switch the Slack agent provider in Settings to a configured cloud provider."
            )
        elif "tool call validation failed" in err_lower:
            log.warning("Slack sub-agent tool validation failed: %s", exc)
            response = (
                "Slack sub-agent could not complete that tool call because the model returned invalid tool arguments. "
                "Please retry the request."
            )
        else:
            log.error("Slack sub-agent error: %s", exc, exc_info=True)
            response = f"Slack sub-agent encountered an error: {exc}"
        return {
            "response":      response,
            "success":       False,
            "delegated_to":  "slack-subagent",
            "refresh_slack": False,
        }
