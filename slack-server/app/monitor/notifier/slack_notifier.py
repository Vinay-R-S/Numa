import logging
import time
from typing import Dict, List, Any
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from app.config import settings

# Configure logging
logger = logging.getLogger(__name__)

# Initialize Slack Client
client = WebClient(token=settings.SLACK_BOT_TOKEN)

def send_slack_dm(summary_text: str = None, summary_data: Dict[str, List[Dict[str, Any]]] = None) -> bool:
    """
    Sends a summary DM to the configured user.
    Supports either pre-formatted text OR structured summary data.
    
    Args:
        summary_text: Optional plain text summary to send.
        summary_data: Optional dictionary for beautiful block formatting.
        
    Returns:
        True if sent successfully, False otherwise.
    """
    recipient_id = settings.NOTIFICATION_USER_ID
    if not recipient_id:
        logger.warning("No NOTIFICATION_USER_ID configured. Cannot send Slack DM.")
        return False
        
    try:
        if summary_data:
            # Send blocks
            blocks = format_summary_blocks(summary_data)
            fallback_text = "Your Slack Summary is here!"
            response = client.chat_postMessage(
                channel=recipient_id,
                blocks=blocks,
                text=fallback_text
            )
        else:
            # Send text
            if not summary_text:
                return False
            response = client.chat_postMessage(
                channel=recipient_id,
                text=summary_text
            )
            
        if response["ok"]:
            logger.info(f"Slack summary sent to {recipient_id}")
            return True
        else:
            logger.error(f"Failed to send Slack DM: {response['error']}")
            return False
            
    except SlackApiError as e:
        logger.error(f"Slack API error sending summary: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error sending Slack summary: {e}")
        return False

def format_summary_blocks(summary_data: Dict[str, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    """Helper to format structured data into Slack blocks."""
    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "🔔 Slack Summary",
                "emoji": True
            }
        },
        {
            "type": "divider"
        }
    ]

    def add_section(title, messages, icon):
        if not messages:
            return
            
        text_content = f"*{title}*\n"
        for msg in messages:
            clean_text = msg.get("text", "").replace("\n", " ").strip()
            if len(clean_text) > 80:
                clean_text = clean_text[:77] + "..."
            text_content += f"• {clean_text}\n"

        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": text_content
            }
        })

    add_section("Mentions", summary_data.get("mentions", []), "👋")
    add_section("Meetings", summary_data.get("meetings", []), "📅")
    add_section("Urgent", summary_data.get("urgent", []), "🚨")
    
    general_msgs = summary_data.get("general", [])
    if general_msgs:
        if len(general_msgs) <= 5:
             add_section("Other", general_msgs, "ℹ️")
        else:
            text_content = "*Other*\n"
            text_content += f"• {len(general_msgs)} general updates\n"
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": text_content
                }
            })
            
    return blocks
