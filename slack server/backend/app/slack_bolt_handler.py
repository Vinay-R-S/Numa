"""
Slack Bolt event handler.
Receives Slack events, saves them to Supabase, and executes NUMA commands.

Mount via FastAPI: app.mount("/slack", slack_app_handler)

Slack events flow:
Slack → POST /slack/events  → BoltApp listener → Supabase
                                        → SlackActionRouter (for /numa commands)
"""
import os
import logging
from datetime import datetime, timezone

from slack_bolt import App
from slack_bolt.adapter.fastapi import SlackRequestHandler

from app.config import settings
from app.database import get_supabase
from app.intent_parser import parse_intent
from app.slack_action_router import SlackActionRouter
from app.agent import run_agent_for_message

logger = logging.getLogger(__name__)

# Bolt auto-enables its own OAuth flow when SLACK_CLIENT_ID / SLACK_CLIENT_SECRET
# exist in the environment. This app handles OAuth itself in app.routers.auth,
# so Bolt must stay in token mode or it will ignore SLACK_BOT_TOKEN.
os.environ.pop("SLACK_CLIENT_ID", None)
os.environ.pop("SLACK_CLIENT_SECRET", None)

try:
    bolt_app = App(
        token=settings.SLACK_BOT_TOKEN,
        signing_secret=settings.SLACK_SIGNING_SECRET,
    )
    bolt_handler = SlackRequestHandler(bolt_app)
    logger.info("Slack Bolt initialized successfully")
except Exception as exc:
    logger.error("Slack Bolt failed to initialize (network issue?): %s", exc)
    bolt_app = None
    bolt_handler = None


# ── Helpers ────────────────────────────────────────────────────────────────────

def _resolve_numa_user(slack_user_id: str, slack_team_id: str):
    """Fetch or auto-create NUMA user record from Supabase."""
    db = get_supabase()
    resp = db.table("users").select("id").eq("slack_user_id", slack_user_id).limit(1).execute()
    if resp.data:
        return resp.data[0]["id"]
    # Auto-create a minimal user record
    ins = db.table("users").insert({
        "slack_user_id": slack_user_id,
        "slack_team_id": slack_team_id,
    }).execute()
    return ins.data[0]["id"]


def _save_message(event: dict, channel_name: str | None = None):
    """Persist a Slack message to the messages table."""
    slack_user_id = event.get("user")
    slack_team_id = event.get("team") or ""
    ts = event.get("ts")
    if not slack_user_id or not ts:
        return

    user_id = _resolve_numa_user(slack_user_id, slack_team_id)

    db = get_supabase()
    db.table("messages").upsert(
        {
            "user_id": user_id,
            "slack_user_id": slack_user_id,
            "slack_team_id": slack_team_id,
            "channel_id": event.get("channel", ""),
            "channel_name": channel_name,
            "text": event.get("text", ""),
            "ts": ts,
            "thread_ts": event.get("thread_ts"),
            "message_type": "message",
            "raw_payload": event,
        },
        on_conflict="ts",
    ).execute()

    # Bump analytics
    _bump(user_id, "messages_sent")


def _bump(user_id: str, field: str):
    from datetime import date
    today = date.today().isoformat()
    db = get_supabase()
    resp = db.table("analytics").select("id," + field).eq("user_id", user_id).eq("period_date", today).limit(1).execute()
    if resp.data:
        row = resp.data[0]
        db.table("analytics").update({field: (row.get(field) or 0) + 1}).eq("id", row["id"]).execute()
    else:
        db.table("analytics").insert({"user_id": user_id, "period_date": today, field: 1}).execute()


# ── Event listeners (only registered when Bolt initialized successfully) ────────

if bolt_app:
    @bolt_app.event("message")
    def handle_message(event: dict, body: dict, say, logger):
        """Capture all messages and handle /numa commands."""
        text: str = event.get("text", "")
        subtype = event.get("subtype")

        # Skip bot messages and edits/deletes
        if event.get("bot_id") or subtype in ("message_changed", "message_deleted", "bot_message"):
            return

        # Resolve channel name if possible
        channel_id = event.get("channel", "")
        channel_name = None
        try:
            from slack_sdk import WebClient
            wc = WebClient(token=settings.SLACK_BOT_TOKEN)
            info = wc.conversations_info(channel=channel_id)
            channel_name = info["channel"].get("name")
        except Exception:
            pass

        # Always persist the message
        _save_message(event, channel_name)

        # team_id is in the outer body, not always in the inner event
        team_id = event.get("team") or body.get("team_id", "")

        # Run agentic analysis for any @mentions or @channel/@here broadcasts
        if any(m in text for m in ("<@", "<!channel>", "<!here>", "<!everyone>")):
            run_agent_for_message(text, event.get("ts"), team_id=team_id)

        # Handle /numa commands
        if text.strip().startswith("/numa") or text.strip().lower().startswith("numa "):
            slack_user_id = event.get("user", "")
            slack_team_id = event.get("team", "")
            user_id = _resolve_numa_user(slack_user_id, slack_team_id)
            _bump(user_id, "commands_used")
            try:
                intent_data = parse_intent(text)
                action_router = SlackActionRouter()
                result = action_router.execute(intent_data, user_id=user_id)
                reply = result.get("message") if result.get("ok") else f"⚠️ {result.get('error')}"
                say(text=reply or "Done.", thread_ts=event.get("ts"))
            except Exception as exc:
                logger.error(f"NUMA command error: {exc}")
                say(text="⚠️ Something went wrong. Please try again.", thread_ts=event.get("ts"))

    @bolt_app.event("app_mention")
    def handle_mention(event: dict, say):
        """Handle @NUMA mentions."""
        text = event.get("text", "")
        slack_user_id = event.get("user", "")
        slack_team_id = event.get("team", "")
        _save_message(event)
        user_id = _resolve_numa_user(slack_user_id, slack_team_id)
        _bump(user_id, "commands_used")
        try:
            intent_data = parse_intent(text)
            action_router = SlackActionRouter()
            result = action_router.execute(intent_data, user_id=user_id)
            reply = result.get("message") if result.get("ok") else f"⚠️ {result.get('error')}"
            say(text=reply or "Done.", thread_ts=event.get("ts"))
        except Exception as exc:
            logger.error(f"Mention error: {exc}")
            say(text="⚠️ Something went wrong.", thread_ts=event.get("ts"))

    @bolt_app.command("/numa")
    def handle_numa_slash(ack, command, say):
        """Handle /numa slash command."""
        ack()
        text = command.get("text", "")
        slack_user_id = command.get("user_id", "")
        slack_team_id = command.get("team_id", "")
        channel_id = command.get("channel_id", "")
        user_id = _resolve_numa_user(slack_user_id, slack_team_id)
        _bump(user_id, "commands_used")
        db = get_supabase()
        from datetime import datetime, timezone
        ts_now = str(datetime.now(timezone.utc).timestamp())
        db.table("messages").insert({
            "user_id": user_id,
            "slack_user_id": slack_user_id,
            "slack_team_id": slack_team_id,
            "channel_id": channel_id,
            "text": f"/numa {text}",
            "ts": ts_now,
            "message_type": "command",
            "raw_payload": command,
        }).execute()
        try:
            full_text = f"/numa {text}" if text else "/numa"
            intent_data = parse_intent(full_text)
            action_router = SlackActionRouter()
            result = action_router.execute(intent_data, user_id=user_id)
            reply = result.get("message") if result.get("ok") else f"⚠️ {result.get('error')}"
            say(text=reply or "Done.")
        except Exception as exc:
            logger.error(f"Slash command error: {exc}")
            say(text="⚠️ Something went wrong.")

    @bolt_app.event("reaction_added")
    def handle_reaction_added(event: dict):
        """Track reactions."""
        slack_user_id = event.get("user", "")
        if not slack_user_id:
            return
        _save_message({
            "user": slack_user_id,
            "team": "",
            "channel": event.get("item", {}).get("channel", ""),
            "text": f":{event.get('reaction')}: reaction added",
            "ts": str(datetime.now(timezone.utc).timestamp()),
            "message_type": "reaction",
        })
