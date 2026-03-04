import logging
import time
from typing import List, Dict, Any
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from app.config import settings
from app.monitor.storage import (
    get_last_checked,
    update_last_checked,
    is_message_processed,
    mark_message_processed,
    initialize_storage
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Slack Client
client = WebClient(token=settings.SLACK_BOT_TOKEN)

def fetch_new_messages(channel_id: str, limit: int = 50) -> List[Dict[str, Any]]:
    """
    Fetch new messages from a Slack channel since the last checked timestamp.
    
    Args:
        channel_id (str): The ID of the Slack channel to fetch from.
        limit (int): Maximum number of messages to fetch in one call. default 50.
        
    Returns:
        List[Dict[str, Any]]: A list of new message objects.
    """
    # ensure storage is initialized
    initialize_storage()
    
    # Get the last timestamp we checked for this channel
    last_checked = get_last_checked(channel_id)
    logger.info(f"Fetching messages for channel {channel_id} since {last_checked}")
    
    new_messages = []
    
    try:
        # Call the conversations.history method using the WebClient
        # oldest: Only messages after this timestamp
        kwargs = {
            "channel": channel_id,
            "limit": limit
        }
        
        # If this is the FIRST time (0.0), let's only fetch the last 20 messages 
        # to avoid overwhelming the system or timing out.
        if not last_checked or float(last_checked) == 0:
             logger.info("First run for channel: fetching recent 20 messages only.")
             kwargs["limit"] = 20
        else:
             # Look back 5 seconds to ensure we don't miss messages due to race conditions
             # Deduplication logic (is_message_processed) prevents re-processing
             safe_ts = float(last_checked) - 5.0
             kwargs["oldest"] = str(safe_ts)
            
        result = client.conversations_history(**kwargs)
        
        messages = result.get("messages", [])
        logger.info(f"Found {len(messages)} potential new messages.")
        
        # Iterate through messages
        # Note: messages are usually returned newest first by default
        max_ts = last_checked
        
        for msg in messages:
            ts = msg.get("ts")
            if not ts:
                continue
                
            # Keep track of the newest timestamp seen in this batch
            if float(ts) > max_ts:
                max_ts = float(ts)
            
            # Skip if already processed
            if is_message_processed(ts):
                logger.debug(f"Skipping already processed message {ts}")
                continue
            
            # Simple check to avoid processing the bot's own messages if needed, 
            # but prompt didn't ask to filter bot messages, so we keep them unless logic dictates otherwise.
            # Usually we might want to skip our own messages.
            # For now, just follow instructions: "Fetch messages newer than that", "Skip messages already marked"
            
            new_messages.append(msg)
            
            # Mark as processed immediately to prevent duplicate processing in case of crash/re-run
            mark_message_processed(ts, channel_id)
            
        # Update the last checked timestamp for the channel to the newest message seen
        # Update the last checked timestamp for the channel to the newest message seen
        if max_ts > last_checked:
            update_last_checked(channel_id, max_ts)
            logger.info(f"Updated last checked timestamp for {channel_id} to {max_ts}")
            
        logger.info(f"After deduplication: {len(new_messages)} new messages to process.")
        return new_messages

    except SlackApiError as e:
        logger.error(f"Error fetching messages: {e}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return []
