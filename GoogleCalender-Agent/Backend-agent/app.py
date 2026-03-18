"""
FastAPI Application
Main application with agent endpoint
"""

import asyncio
import os
import uuid
from datetime import datetime, timedelta
from typing import AsyncGenerator, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from langchain_core.messages import AIMessage, HumanMessage
from agent.graph import agent_graph
from services.calendar_service import IST, get_calendar_service
import uvicorn


# Initialize FastAPI app
app = FastAPI(
    title="Google Calendar & Gmail Agent API",
    description="LangGraph agent for managing calendar events and emails",
    version="1.0.0"
)

WATCH_WEBHOOK_TOKEN = os.getenv("WATCH_WEBHOOK_TOKEN", "")
GOOGLE_WEBHOOK_BASE_URL = os.getenv("GOOGLE_WEBHOOK_BASE_URL", "")

watch_state: Dict[str, Optional[str]] = {
    "channel_id": None,
    "resource_id": None,
    "expiration": None,
    "last_message_number": None,
}
watch_version = 0

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8080",
        "http://127.0.0.1:8080",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatHistoryMessage(BaseModel):
    """Lightweight chat history item used by frontend conversations."""
    role: str
    content: str


class AgentRequest(BaseModel):
    """Request model for agent endpoint"""
    query: str = Field(..., description="User query to send to the agent")
    history: List[ChatHistoryMessage] = Field(default_factory=list, description="Prior chat messages for conversational context")
    
    class Config:
        json_schema_extra = {
            "example": {
                "query": "Schedule a meeting tomorrow at 2pm titled 'Team Sync'"
            }
        }


class AgentResponse(BaseModel):
    """Response model for agent endpoint"""
    response: str
    success: bool
    refreshCalendar: bool = False


class CalendarEvent(BaseModel):
    """Frontend-friendly calendar event model"""
    id: str
    title: str
    date: str
    startTime: str
    endTime: str
    description: str
    color: Optional[str] = None
    calendarName: Optional[str] = None
    readonly: bool = False


class EventsResponse(BaseModel):
    """Response model for events endpoint"""
    events: List[CalendarEvent]


class CalendarEventUpsert(BaseModel):
    """Create or update payload for calendar events."""
    title: str
    date: str
    startTime: str
    endTime: str
    description: str = ""


class DeleteResponse(BaseModel):
    """Response model for delete endpoint."""
    success: bool


class HealthResponse(BaseModel):
    """Backend status response."""
    status: str
    message: str


class WatchStartResponse(BaseModel):
    """Response model for watch registration endpoint."""
    success: bool
    channel_id: str
    resource_id: str
    expiration: Optional[str] = None


class WatchStateResponse(BaseModel):
    """Current watch status for diagnostics."""
    active: bool
    channel_id: Optional[str] = None
    resource_id: Optional[str] = None
    expiration: Optional[str] = None


def _format_event_for_frontend(event: Dict) -> CalendarEvent:
    """Normalize Google event payload to frontend event shape."""
    start_data = event.get("start", {})
    end_data = event.get("end", {})

    start_dt_raw = start_data.get("dateTime")
    end_dt_raw = end_data.get("dateTime")

    if start_dt_raw:
        start_dt = datetime.fromisoformat(start_dt_raw.replace("Z", "+00:00")).astimezone(IST)
        event_date = start_dt.date().isoformat()
        start_time = start_dt.strftime("%H:%M")
    else:
        # All-day events use date-only fields from Google Calendar.
        event_date = start_data.get("date", datetime.now(IST).date().isoformat())
        start_time = "00:00"

    if end_dt_raw:
        end_dt = datetime.fromisoformat(end_dt_raw.replace("Z", "+00:00")).astimezone(IST)
        end_time = end_dt.strftime("%H:%M")
    else:
        end_time = "23:59"

    calendar_name = event.get("_calendar_summary")
    is_readonly = event.get("_calendar_access_role") not in (None, "owner", "writer")
    event_id = event.get("id", "")
    calendar_id = event.get("_calendar_id")
    safe_id = event_id if not is_readonly else f"{calendar_id}:{event_id}"

    description = event.get("description", "")
    if not description and calendar_name:
        description = f"From {calendar_name}"

    return CalendarEvent(
        id=safe_id,
        title=event.get("summary", "(No title)"),
        date=event_date,
        startTime=start_time,
        endTime=end_time,
        description=description,
        color=None,
        calendarName=calendar_name,
        readonly=is_readonly,
    )


def _list_selected_calendars(service) -> List[Dict[str, Optional[str]]]:
    """List selected/primary calendars available to the authenticated user."""
    response = service.calendarList().list().execute()
    calendars: List[Dict[str, Optional[str]]] = []

    for cal in response.get("items", []):
        if cal.get("primary") or cal.get("selected", True):
            calendars.append({
                "id": cal.get("id"),
                "summary": cal.get("summary"),
                "accessRole": cal.get("accessRole"),
            })

    return calendars


def _collect_events_across_calendars(service, time_min: str, time_max: str) -> List[Dict]:
    """Fetch events across selected calendars and attach source metadata."""
    combined_events: List[Dict] = []

    for cal in _list_selected_calendars(service):
        cal_id = cal.get("id")
        if not cal_id:
            continue

        events_result = service.events().list(
            calendarId=cal_id,
            timeMin=time_min,
            timeMax=time_max,
            singleEvents=True,
            orderBy="startTime",
        ).execute()

        for event in events_result.get("items", []):
            event["_calendar_id"] = cal_id
            event["_calendar_summary"] = cal.get("summary")
            event["_calendar_access_role"] = cal.get("accessRole")
            combined_events.append(event)

    combined_events.sort(key=lambda e: e.get("start", {}).get("dateTime", e.get("start", {}).get("date", "")))
    return combined_events


def _parse_datetime_fields(date_str: str, time_str: str) -> datetime:
    """Parse date and time fields from frontend payload into IST datetime."""
    parsed = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
    return IST.localize(parsed)


def _build_google_event_body(payload: CalendarEventUpsert) -> Dict:
    """Build Google Calendar event body from frontend payload."""
    start_dt = _parse_datetime_fields(payload.date, payload.startTime)
    end_dt = _parse_datetime_fields(payload.date, payload.endTime)

    if end_dt <= start_dt:
        raise HTTPException(status_code=400, detail="endTime must be after startTime")

    return {
        "summary": payload.title.strip() or "(No title)",
        "description": payload.description,
        "start": {
            "dateTime": start_dt.isoformat(),
            "timeZone": "Asia/Kolkata",
        },
        "end": {
            "dateTime": end_dt.isoformat(),
            "timeZone": "Asia/Kolkata",
        },
    }


def _touch_watch_version() -> None:
    """Increment server-side calendar version for SSE subscribers."""
    global watch_version
    watch_version += 1


def _parse_google_expiration(expiration_ms: Optional[str]) -> Optional[str]:
    """Convert Google expiration millis string to ISO timestamp."""
    if not expiration_ms:
        return None

    try:
        expiration_int = int(expiration_ms)
        return datetime.fromtimestamp(expiration_int / 1000).isoformat()
    except (TypeError, ValueError):
        return None


@app.get("/", response_model=HealthResponse)
async def root():
    """Health check endpoint"""
    return {
        "status": "running",
        "message": "Google Calendar & Gmail Agent API"
    }


@app.get("/health", response_model=HealthResponse)
async def health():
    """Explicit health endpoint for frontend connection checks."""
    return {
        "status": "running",
        "message": "Google Calendar & Gmail Agent API"
    }


@app.get("/watch/status", response_model=WatchStateResponse)
async def watch_status():
    """Expose current Google watch registration status."""
    return WatchStateResponse(
        active=bool(watch_state.get("channel_id") and watch_state.get("resource_id")),
        channel_id=watch_state.get("channel_id"),
        resource_id=watch_state.get("resource_id"),
        expiration=watch_state.get("expiration"),
    )


@app.post("/watch/start", response_model=WatchStartResponse)
async def start_calendar_watch():
    """Create or replace Google Calendar push watch channel."""
    callback_base = GOOGLE_WEBHOOK_BASE_URL.strip()
    if not callback_base:
        raise HTTPException(
            status_code=400,
            detail="GOOGLE_WEBHOOK_BASE_URL is not configured",
        )

    callback_url = f"{callback_base.rstrip('/')}/webhooks/google-calendar"
    channel_id = str(uuid.uuid4())
    token = WATCH_WEBHOOK_TOKEN or str(uuid.uuid4())

    try:
        service = get_calendar_service()

        response = service.events().watch(
            calendarId="primary",
            body={
                "id": channel_id,
                "type": "web_hook",
                "address": callback_url,
                "token": token,
            },
        ).execute()

        watch_state["channel_id"] = response.get("id")
        watch_state["resource_id"] = response.get("resourceId")
        watch_state["expiration"] = _parse_google_expiration(response.get("expiration"))
        watch_state["last_message_number"] = None

        return WatchStartResponse(
            success=True,
            channel_id=response.get("id", channel_id),
            resource_id=response.get("resourceId", ""),
            expiration=_parse_google_expiration(response.get("expiration")),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start watch: {str(e)}") from e


@app.post("/webhooks/google-calendar")
async def google_calendar_webhook(request):
    """Receive Google Calendar push notifications and fan out via SSE."""
    channel_id = request.headers.get("X-Goog-Channel-Id")
    resource_id = request.headers.get("X-Goog-Resource-Id")
    message_number = request.headers.get("X-Goog-Message-Number")
    token = request.headers.get("X-Goog-Channel-Token", "")

    if WATCH_WEBHOOK_TOKEN and token != WATCH_WEBHOOK_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid webhook token")

    if watch_state.get("channel_id") and channel_id != watch_state.get("channel_id"):
        raise HTTPException(status_code=400, detail="Unknown channel id")

    if watch_state.get("resource_id") and resource_id != watch_state.get("resource_id"):
        raise HTTPException(status_code=400, detail="Unknown resource id")

    if message_number and message_number != watch_state.get("last_message_number"):
        watch_state["last_message_number"] = message_number
        _touch_watch_version()

    return {"ok": True}


@app.get("/events/stream")
async def stream_event_updates():
    """SSE endpoint used by frontend to receive real-time calendar update ticks."""

    async def event_generator() -> AsyncGenerator[str, None]:
        local_version = watch_version

        while True:
            if local_version != watch_version:
                local_version = watch_version
                yield f"event: calendar-updated\ndata: {{\"version\": {watch_version}}}\n\n"

            yield "event: keepalive\ndata: ping\n\n"
            await asyncio.sleep(8)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/events", response_model=EventsResponse)
async def get_events(days: int = 60):
    """Fetch calendar events for frontend rendering (past 60 days + future window)."""
    if days < 1:
        raise HTTPException(status_code=400, detail="days must be >= 1")

    try:
        service = get_calendar_service()
        now = datetime.now(IST)
        # Start of today (midnight) minus 60 days so past events are included
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        time_min = (today_start - timedelta(days=60)).isoformat()
        time_max = (today_start + timedelta(days=days)).isoformat()
        events_raw = _collect_events_across_calendars(service, time_min, time_max)
        events = [_format_event_for_frontend(event) for event in events_raw]
        return EventsResponse(events=events)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch events: {str(e)}") from e


@app.post("/events", response_model=CalendarEvent)
async def create_event(payload: CalendarEventUpsert):
    """Create a Google Calendar event from frontend form data."""
    try:
        service = get_calendar_service()
        body = _build_google_event_body(payload)
        created = service.events().insert(calendarId="primary", body=body).execute()
        _touch_watch_version()
        return _format_event_for_frontend(created)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create event: {str(e)}") from e


@app.put("/events/{event_id}", response_model=CalendarEvent)
async def update_event(event_id: str, payload: CalendarEventUpsert):
    """Update title/description/time for an existing Google Calendar event."""
    try:
        service = get_calendar_service()
        body = _build_google_event_body(payload)
        updated = service.events().patch(calendarId="primary", eventId=event_id, body=body).execute()
        _touch_watch_version()
        return _format_event_for_frontend(updated)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update event: {str(e)}") from e


@app.delete("/events/{event_id}", response_model=DeleteResponse)
async def delete_event(event_id: str):
    """Delete a Google Calendar event."""
    try:
        service = get_calendar_service()
        service.events().delete(calendarId="primary", eventId=event_id).execute()
        _touch_watch_version()
        return DeleteResponse(success=True)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete event: {str(e)}") from e


@app.post("/agent", response_model=AgentResponse)
async def run_agent(request: AgentRequest):
    """
    Run the LangGraph agent with user query
    
    Args:
        request: AgentRequest with user query
    
    Returns:
        AgentResponse: Agent's response and success status
    """
    try:
        user_query = request.query
        history_messages = []

        for message in request.history:
            if not message.content.strip():
                continue

            role = message.role.lower()
            if role == "user":
                history_messages.append(HumanMessage(content=message.content))
            elif role in ("assistant", "ai"):
                history_messages.append(AIMessage(content=message.content))
        
        initial_state = {
            "messages": history_messages + [HumanMessage(content=user_query)],
            "user_query": user_query
        }
        
        # Run agent graph
        result = agent_graph.invoke(initial_state)
        
        # Extract final response from messages
        messages = result.get('messages', [])
        
        if not messages:
            raise HTTPException(
                status_code=500,
                detail="Agent did not produce any response"
            )
        
        # Get the last AI message
        final_message = messages[-1]
        response_text = final_message.content
        
        mutation_keywords = (
            "schedule",
            "create",
            "add",
            "delete",
            "remove",
            "cancel",
            "reschedule",
            "move",
            "modify",
            "update",
            "undo",
        )
        # Check user query for mutation intent
        query_has_mutation = any(word in user_query.lower() for word in mutation_keywords)
        # Also check agent response for confirmation of a real mutation (handles pronoun cases like "delete this")
        response_confirms_mutation = any(phrase in response_text for phrase in (
            "✓ Event created", "✓ Event deleted", "Event deleted", "Event created",
            "rescheduled", "modified", "updated", "deleted successfully", "created successfully",
        ))
        refresh_calendar = query_has_mutation or response_confirms_mutation

        return AgentResponse(
            response=response_text,
            success=True,
            refreshCalendar=refresh_calendar,
        )
        
    except Exception as e:
        # Log error and return error response
        error_msg = f"Error running agent: {str(e)}"
        print(error_msg)
        
        return AgentResponse(
            response=error_msg,
            success=False,
            refreshCalendar=False,
        )


if __name__ == "__main__":
    # Run server
    print("🚀 Starting FastAPI server...")
    print("📝 API Documentation: http://localhost:8000/docs")
    print("🔧 Agent endpoint: POST http://localhost:8000/agent")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
