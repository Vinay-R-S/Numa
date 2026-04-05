"""
Slack DM notifier — sends formatted block messages to the configured user.
"""
import logging
from typing import Dict, List, Any

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from app.config import settings

logger = logging.getLogger(__name__)

_client: WebClient | None = None


def _get_client() -> WebClient:
    global _client
    if _client is None:
        _client = WebClient(token=settings.SLACK_BOT_TOKEN)
    return _client


def _build_blocks(summary: Dict[str, List[Dict[str, Any]]]) -> List[Dict]:
    blocks: List[Dict] = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": "📬 NUMA — Slack Activity Summary", "emoji": True},
        },
        {"type": "divider"},
    ]

    SECTION_META = [
        ("mentions", "👋 Mentions",  "#E91E63"),
        ("meetings", "📅 Meetings",  "#2196F3"),
        ("urgent",   "🚨 Urgent",    "#FF5722"),
        ("general",  "📢 General",   "#607D8B"),
    ]

    for key, title, _ in SECTION_META:
        items = summary.get(key, [])
        if not items:
            continue
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*{title}*  ·  {len(items)} message(s)"},
        })
        for msg in items[:5]:      # cap at 5 per section to keep DM readable
            text = msg.get("text", "").replace("\n", " ")[:200]
            channel = msg.get("channel_id", "")
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"> {text}" + (f"\n_in <#{channel}>_" if channel else ""),
                },
            })

    blocks.append({"type": "divider"})
    blocks.append({
        "type": "context",
        "elements": [{"type": "mrkdwn", "text": "Reply or type `/numa help` to interact with NUMA."}],
    })
    return blocks


def send_slack_dm(
    summary_data: Dict[str, List[Dict[str, Any]]] | None = None,
    summary_text: str | None = None,
) -> bool:
    """
    Send a summary DM to NOTIFICATION_USER_ID.
    Prefers block-formatted output when summary_data is provided.
    """
    recipient = settings.NOTIFICATION_USER_ID
    if not recipient:
        logger.warning("NOTIFICATION_USER_ID not set — skipping Slack DM.")
        return False

    try:
        if summary_data:
            blocks = _build_blocks(summary_data)
            resp = _get_client().chat_postMessage(
                channel=recipient,
                blocks=blocks,
                text="NUMA Slack Activity Summary",
            )
        elif summary_text:
            resp = _get_client().chat_postMessage(channel=recipient, text=summary_text)
        else:
            return False

        if resp["ok"]:
            logger.info("Slack DM sent to %s", recipient)
            return True

        logger.error("Slack DM failed: %s", resp.get("error"))
        return False

    except SlackApiError as exc:
        logger.error("Slack API error: %s", exc.response["error"])
        return False
    except Exception as exc:
        logger.error("Unexpected error sending Slack DM: %s", exc)
        return False
