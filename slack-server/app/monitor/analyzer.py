from typing import List, Dict, Any

def analyze_messages(messages: List[Dict[str, Any]], user_id: str = None) -> Dict[str, List[Dict[str, Any]]]:
    """
    Analyze a list of Slack messages to detect mentions and keywords.
    
    Args:
        messages: List of Slack message dictionaries.
        user_id: The ID of the bot/user to detect mentions for (e.g., U12345).
        
    Returns:
        Structured dictionary with keys: mentions, meetings, urgent, general.
    """
    result = {
        "mentions": [],
        "meetings": [],
        "urgent": [],
        "general": []
    }
    
    if not messages:
        return result

    # Standardize keywords to lowercase for case-insensitive matching
    MEETING_KEYWORDS = {"meeting"}
    URGENT_KEYWORDS = {"urgent", "deadline", "asap"}
    # Group 'tomorrow' and 'reminder' under general as they are task-related
    GENERAL_KEYWORDS = {"tomorrow", "reminder"}
    
    user_mention_tag = f"<@{user_id}>" if user_id else None
    
    for msg in messages:
        # Skip messages without text
        text = msg.get("text", "")
        if not text:
            # Check for attachments or blocks if text is empty? 
            # For simplicity, we stick to text. blocks usually have text too.
            continue
            
        # Skip bot messages if desired (often have 'bot_id' or 'subtype')
        if msg.get("bot_id") and msg.get("bot_id") != "B00000000": # Allow specific bot debugging if needed, but generally skip
             # However, prompt says "Skip bot messages if needed". 
             # Let's be safe and skip them to avoid loops, unless it's really important.
             continue
        if msg.get("subtype") == "bot_message":
            continue
            
        text_lower = text.lower()
        
        # 1. Check for Mentions
        is_mentioned = False
        if user_mention_tag and user_mention_tag in text:
            result["mentions"].append(msg)
            is_mentioned = True
            
        # 2. Check for Keywords
        # We classify based on priority: Meeting > Urgent > General
        # A message can be in multiple categories? 
        # The prompt structure implies a partition or potential overlap.
        # Usually, a message is filed under its most significant trait, 
        # or duplicated if we want to show it in all relevant lists.
        # Let's duplicate it if it matches multiple, so we don't miss context.
        
        # Check Meeting
        if any(k in text_lower for k in MEETING_KEYWORDS):
            result["meetings"].append(msg)
            
        # Check Urgent
        if any(k in text_lower for k in URGENT_KEYWORDS):
            result["urgent"].append(msg)
            
        # Check General (Tomorrow, Reminder)
        is_categorized = False
        if any(k in text_lower for k in GENERAL_KEYWORDS):
            result["general"].append(msg)
            is_categorized = True
            
        # If not categorized by keywords and not a mention, add to 'general' anyway 
        # to ensure we don't silently drop messages the user asked to monitor.
        if not is_categorized and not is_mentioned and not any(k in text_lower for k in MEETING_KEYWORDS) and not any(k in text_lower for k in URGENT_KEYWORDS):
             result["general"].append(msg)
            
    return result
