"""
LangChain Tools
Defines tools for calendar and email operations
"""

from langchain_core.tools import tool
from services.calendar_service import (
    create_calendar_event, list_upcoming_events,
    delete_calendar_event, delete_event_by_text
)
from services.gmail_service import send_email


@tool
def schedule_event(title: str, datetime_str: str, duration_minutes: int = 60) -> str:
    """
    Schedule a new calendar event in Google Calendar.
    
    Args:
        title: Event title/summary
        datetime_str: Event start time in ISO format (e.g., "2026-02-15T14:00:00")
        duration_minutes: Event duration in minutes (default: 60)
    
    Returns:
        str: Success message with event details
    """
    try:
        result = create_calendar_event(title, datetime_str, duration_minutes)
        
        # Handle duplicate prevention
        if result.get('status') == 'duplicate_prevented':
            return (
                f"⚠ Duplicate event detected — not created.\n"
                f"Title: {result['summary']}\n"
                f"Start: {result['start']}"
            )
        
        return (
            f"✓ Event created successfully!\n"
            f"Title: {result['summary']}\n"
            f"Start: {result['start']}\n"
            f"Link: {result['link']}"
        )
    except Exception as e:
        return f"✗ Error creating event: {str(e)}"


@tool
def get_events(days: int = 1) -> str:
    """
    Get upcoming calendar events from Google Calendar.
    
    Args:
        days: Number of days ahead to look (default: 1)
    
    Returns:
        str: Human-readable list of upcoming events, or a message if none found
    """
    try:
        events = list_upcoming_events(days)
        
        if not events:
            return "No upcoming events found."
        
        lines = []
        for event in events:
            lines.append(f"• {event['summary']} at {event['start']}")
        
        return f"Upcoming events ({len(events)}):\n" + "\n".join(lines)
    except Exception as e:
        return f"✗ Error fetching events: {str(e)}"


@tool
def delete_event(event_id: str) -> str:
    """
    Delete a calendar event by its event ID.
    
    Args:
        event_id: The Google Calendar event ID to delete
    
    Returns:
        str: Confirmation message or error
    """
    try:
        result = delete_calendar_event(event_id)
        return f"✓ Event deleted successfully. (ID: {result['deleted_event_id']})"
    except Exception as e:
        return f"✗ Error deleting event: {str(e)}"


@tool
def delete_by_text(search_text: str) -> str:
    """
    Delete a calendar event using a natural language description.
    Searches upcoming events (next 7 days) for a matching title and deletes it.
    
    Args:
        search_text: Natural language phrase describing the event (e.g. "gym", "dentist", "meeting with Rahul")
    
    Returns:
        str: Confirmation of deletion or message if no match found
    """
    try:
        result = delete_event_by_text(search_text)
        
        if result['status'] == 'not_found':
            return result['message']
        
        return (
            f"✓ Event deleted successfully!\n"
            f"Title: {result['deleted_summary']}\n"
            f"Was at: {result['deleted_start']}"
        )
    except Exception as e:
        return f"✗ Error deleting event: {str(e)}"


@tool
def send_gmail(to: str, subject: str, body: str) -> str:
    """
    Send an email via Gmail.
    
    Args:
        to: Recipient email address
        subject: Email subject line
        body: Email body content
    
    Returns:
        str: Success message with sent email details
    """
    try:
        result = send_email(to, subject, body)
        return (
            f"✓ Email sent successfully!\n"
            f"To: {result['to']}\n"
            f"Subject: {result['subject']}\n"
            f"Message ID: {result['message_id']}"
        )
    except Exception as e:
        return f"✗ Error sending email: {str(e)}"


# Export tools list — all tools available to the agent
TOOLS = [schedule_event, get_events, delete_event, delete_by_text, send_gmail]
