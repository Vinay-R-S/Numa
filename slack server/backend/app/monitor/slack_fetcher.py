"""
Slack message fetcher — pulls channel history, persists it, and de-duplicates via Supabase.
"""
import logging
from typing import List, Dict, Any

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from app.config import settings
from app.database import get_supabase
from app.agent import run_agent_for_message

logger = logging.getLogger(__name__)

_slack_client: WebClient | None = None
_team_id: str | None = None
_channel_names: dict[str, str | None] = {}


def _client() -> WebClient:
    global _slack_client
    if _slack_client is None:
        _slack_client = WebClient(token=settings.SLACK_BOT_TOKEN)
    return _slack_client


def _get_team_id() -> str:
    global _team_id
    if _team_id is None:
        try:
            _team_id = _client().auth_test().get("team_id", "")
        except SlackApiError as exc:
            logger.warning("Could not resolve Slack team id: %s", exc.response.get("error"))
            _team_id = ""
    return _team_id


def _get_channel_name(channel_id: str) -> str | None:
    if channel_id not in _channel_names:
        try:
            info = _client().conversations_info(channel=channel_id)
            _channel_names[channel_id] = info.get("channel", {}).get("name")
        except SlackApiError as exc:
            logger.warning("Could not resolve channel name for %s: %s", channel_id, exc.response.get("error"))
            _channel_names[channel_id] = None
    return _channel_names[channel_id]


def _resolve_numa_user(slack_user_id: str, slack_team_id: str) -> str | None:
    if not slack_user_id:
        return None

    db = get_supabase()
    resp = db.table("users").select("id").eq("slack_user_id", slack_user_id).limit(1).execute()
    if resp.data:
        return resp.data[0]["id"]

    try:
        ins = db.table("users").insert({
            "slack_user_id": slack_user_id,
            "slack_team_id": slack_team_id or _get_team_id(),
        }).execute()
        return ins.data[0]["id"]
    except Exception as exc:
        logger.warning("Could not auto-create user for %s: %s", slack_user_id, exc)
        return None


def _persist_message(channel_id: str, msg: Dict[str, Any]) -> None:
    ts = msg.get("ts")
    slack_user_id = msg.get("user")
    if not ts or not slack_user_id:
        return

    slack_team_id = _get_team_id()
    user_id = _resolve_numa_user(slack_user_id, slack_team_id)

    get_supabase().table("messages").upsert(
        {
            "user_id": user_id,
            "slack_user_id": slack_user_id,
            "slack_team_id": slack_team_id,
            "channel_id": channel_id,
            "channel_name": _get_channel_name(channel_id),
            "text": msg.get("text", ""),
            "ts": ts,
            "thread_ts": msg.get("thread_ts"),
            "message_type": msg.get("subtype") or "message",
            "raw_payload": msg,
        },
        on_conflict="ts",
    ).execute()


# --- Supabase-backed state helpers ---

def _get_last_checked(channel_id: str) -> float:
    """Return the timestamp of the last fetched message for a channel (0.0 if none)."""
    try:
        row = (
            get_supabase()
            .table("monitor_state")
            .select("last_ts")
            .eq("channel_id", channel_id)
            .maybe_single()
            .execute()
        )
        if row.data:
            return float(row.data["last_ts"])
    except Exception:
        pass
    return 0.0


def _update_last_checked(channel_id: str, ts: float) -> None:
    get_supabase().table("monitor_state").upsert(
        {"channel_id": channel_id, "last_ts": str(ts)},
        on_conflict="channel_id",
    ).execute()


def _is_processed(ts: str) -> bool:
    row = (
        get_supabase()
        .table("processed_messages")
        .select("ts")
        .eq("ts", ts)
        .maybe_single()
        .execute()
    )
    return row.data is not None


def _mark_processed(ts: str) -> None:
    try:
        get_supabase().table("processed_messages").insert({"ts": ts}).execute()
    except Exception:
        pass


# --- Public API ---

def fetch_new_messages(channel_id: str, limit: int = 50) -> List[Dict[str, Any]]:
    """
    Fetch new (unprocessed) messages from a Slack channel since the last run.
    Marks each returned message as processed in Supabase.
    """
    last_checked = _get_last_checked(channel_id)
    logger.info("Fetching channel %s since ts=%s", channel_id, last_checked)

    kwargs: Dict[str, Any] = {"channel": channel_id, "limit": limit}
    if last_checked == 0.0:
        kwargs["limit"] = 20  # first run — small batch
    else:
        # Pull 5 s back to handle clock skew; deduplication prevents re-processing
        kwargs["oldest"] = str(last_checked - 5.0)

    try:
        result = _client().conversations_history(**kwargs)
    except SlackApiError as exc:
        logger.error("Slack API error fetching %s: %s", channel_id, exc.response["error"])
        return []

    messages = result.get("messages", [])
    logger.info("Got %d candidate messages from %s", len(messages), channel_id)

    new_messages: List[Dict[str, Any]] = []
    max_ts = last_checked

    for msg in messages:
        ts = msg.get("ts")
        if not ts:
            continue

        float_ts = float(ts)
        if float_ts > max_ts:
            max_ts = float_ts

        if _is_processed(ts):
            continue

        # Skip bot messages to avoid feedback loops
        if msg.get("bot_id") or msg.get("subtype") == "bot_message":
            _mark_processed(ts)
            continue

        _mark_processed(ts)
        msg["channel_id"] = channel_id
        _persist_message(channel_id, msg)

        # Run agentic analysis for mentions and broadcasts
        text = msg.get("text", "")
        if any(m in text for m in ("<@", "<!channel>", "<!here>", "<!everyone>")):
            run_agent_for_message(text, ts, team_id=_get_team_id())

        new_messages.append(msg)

    if max_ts > last_checked:
        _update_last_checked(channel_id, max_ts)

    logger.info("Returning %d new messages from %s", len(new_messages), channel_id)
    return new_messages
