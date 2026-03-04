import logging
from typing import Dict, List, Any
from app.config import settings
from app.monitor.notifier.email_notifier import send_email
from app.monitor.notifier.slack_notifier import send_slack_dm
from app.monitor.storage import log_notification

logger = logging.getLogger(__name__)

def dispatch_notifications(summary_data: Dict[str, List[Dict[str, Any]]]):
    """
    Central function to dispatch notifications via Email and Slack.
    
    Args:
        summary_data: Structured dictionary of summary information.
    """
    # Check if there's anything to report
    total_messages = sum(len(msgs) for msgs in summary_data.values())
    if total_messages == 0:
        logger.info("No important messages to report. Skipping notifications.")
        return

    logger.info(f"Dispatching notifications for {total_messages} messages.")
    
    email_sent = False
    slack_sent = False
    
    # 1. Email Notification
    if settings.EMAIL_ENABLED:
        email_body = format_summary_text(summary_data)
        email_sent = send_email(email_body)
    else:
        logger.debug("Email notifications disabled.")
        
    # 2. Slack Notification
    # We pass the structured data for nicer formatting
    slack_sent = send_slack_dm(summary_data=summary_data)
    
    # Log results
    if email_sent:
        log_notification("email_summary", f"Sent email summary ({total_messages} items)")
        
    if slack_sent:
        log_notification("slack_summary", f"Sent Slack summary ({total_messages} items)")
        
    if not (email_sent or slack_sent):
        if settings.EMAIL_ENABLED: # Only critically fail if we expected some output
            logger.error("Failed to send BOTH Email and Slack notifications.")
        else:
            if not slack_sent:
                logger.error("Failed to send Slack notification.")

def format_summary_text(summary_data: Dict[str, List[Dict[str, Any]]]) -> str:
    """Helper to format structured data into plain text for Email."""
    lines = ["Slack Summary (Last 15 Minutes)\n"]
    
    def add_section(title, messages):
        if not messages:
            return
        lines.append(f"\n{title}:")
        for msg in messages:
            clean_text = msg.get("text", "").replace("\n", " ").strip()
            if len(clean_text) > 100:
                clean_text = clean_text[:97] + "..."
            lines.append(f"- {clean_text}")
            
    add_section("Mentions", summary_data.get("mentions", []))
    add_section("Meetings", summary_data.get("meetings", []))
    add_section("Urgent", summary_data.get("urgent", []))
    
    general_msgs = summary_data.get("general", [])
    if general_msgs:
        if len(general_msgs) <= 5:
            add_section("Other", general_msgs)
        else:
            lines.append(f"\nOther:")
            lines.append(f"- {len(general_msgs)} general updates")
            
    return "\n".join(lines)
