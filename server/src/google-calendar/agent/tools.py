"""
LangChain Tools
Defines tools for calendar and email operations
"""

from langchain_core.tools import tool
from services.calendar_service import (
    create_calendar_event, list_upcoming_events,
    delete_calendar_event, delete_event_by_description,
    modify_event_by_description, find_free_slots as find_free_slots_service
)
from services.gmail_service import send_email


@tool
def schedule_event(title: str, datetime_str: str, duration_minutes: int = 60, attendees: list = None) -> str:
    """
    Schedule a new calendar event in Google Calendar with automatic Google Meet link.
    
    Args:
        title: Event title/summary
        datetime_str: Event start time in ISO format (e.g., "2026-02-15T14:00:00")
        duration_minutes: Event duration in minutes (default: 60)
        attendees: Optional list of attendee email addresses (e.g. ["john@example.com", "jane@example.com"])
    
    Returns:
        str: Success message with event details, Meet link, and attendees
    """
    try:
        result = create_calendar_event(title, datetime_str, duration_minutes, attendees)
        
        # Handle duplicate prevention
        if result.get('status') == 'duplicate_prevented':
            return (
                f"⚠ Duplicate event detected — not created.\n"
                f"Title: {result['summary']}\n"
                f"Start: {result['start']}"
            )
        
        msg = (
            f"✓ Event created successfully!\n"
            f"Title: {result['summary']}\n"
            f"Start: {result['start']}\n"
            f"Link: {result['link']}"
        )
        if result.get('meet_link'):
            msg += f"\nMeet: {result['meet_link']}"
        if result.get('attendees'):
            msg += f"\nAttendees: {', '.join(result['attendees'])}"
        return msg
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
            lines.append(f"• {event['summary']} at {event['start']} (ID: {event['id']})")
        
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
def delete_by_description(query: str) -> str:
    """
    Delete a calendar event using a natural language description.
    Searches upcoming events (next 7 days) for matching titles using fuzzy, case-insensitive partial matching.
    If exactly one match is found, it is deleted automatically.
    If multiple matches are found, a list is returned for clarification.
    
    Args:
        query: Natural language phrase describing the event (e.g. "gym", "dentist", "meeting with Rahul")
    
    Returns:
        str: Confirmation of deletion, list of matches for clarification, or not-found message
    """
    try:
        result = delete_event_by_description(query)
        
        if result['status'] == 'not_found':
            return result['message']
        
        if result['status'] == 'deleted':
            return (
                f"✓ Event deleted successfully!\n"
                f"Title: {result['deleted_summary']}\n"
                f"Was at: {result['deleted_start']}"
            )
        
        if result['status'] == 'multiple_matches':
            lines = [result['message']]
            for i, m in enumerate(result['matches'], 1):
                lines.append(f"  {i}. {m['summary']} at {m['start']}")
            return "\n".join(lines)
        
        return "Unexpected result from deletion service."
    except Exception as e:
        return f"✗ Error deleting event: {str(e)}"


@tool
def modify_event(query: str, new_datetime_str: str) -> str:
    """
    Reschedule a calendar event found by natural language description.
    Searches upcoming events (next 7 days) for a fuzzy title match.
    Preserves original duration unless the user specifies a new one.
    
    Args:
        query: Natural language phrase identifying the event (e.g. "gym", "meeting with Rahul")
        new_datetime_str: New start time in ISO format (e.g. "2026-02-16T14:00:00")
    
    Returns:
        str: Confirmation of modification, list of matches for clarification, or not-found message
    """
    try:
        result = modify_event_by_description(query, new_datetime_str)
        
        if result['status'] == 'not_found':
            return result['message']
        
        if result['status'] == 'modified':
            return (
                f"✓ Event rescheduled successfully!\n"
                f"Title: {result['summary']}\n"
                f"Old time: {result['old_start']}\n"
                f"New time: {result['new_start']}\n"
                f"Duration: {result['duration_minutes']} min (preserved)\n"
                f"Link: {result['link']}"
            )
        
        if result['status'] == 'multiple_matches':
            lines = [result['message']]
            for i, m in enumerate(result['matches'], 1):
                lines.append(f"  {i}. {m['summary']} at {m['start']}")
            return "\n".join(lines)
        
        return "Unexpected result from modification service."
    except Exception as e:
        return f"✗ Error modifying event: {str(e)}"


@tool
def find_free_slots(date: str, duration_minutes: int = 30) -> str:
    """
    Find available free time slots on a given date.
    Scans events between 08:00 and 22:00 IST, computes gaps, and returns
    intervals large enough for the requested duration.
    
    Args:
        date: Target date in YYYY-MM-DD format
        duration_minutes: Minimum required slot length in minutes (default: 30)
    
    Returns:
        str: Human-readable list of free slots with start, end, and duration
    """
    try:
        result = find_free_slots_service(date, duration_minutes)
        
        if not result['free_slots']:
            return f"No free slots of {duration_minutes}+ minutes found on {result['date']}."
        
        lines = [f"Free slots on {result['date']} (≥{duration_minutes} min):"]
        for slot in result['free_slots']:
            lines.append(f"  • {slot['start']} – {slot['end']} ({slot['duration_minutes']} min)")
        
        return "\n".join(lines)
    except Exception as e:
        return f"✗ Error finding free slots: {str(e)}"


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
TOOLS = [schedule_event, get_events, delete_event, delete_by_description, modify_event, find_free_slots, send_gmail]

