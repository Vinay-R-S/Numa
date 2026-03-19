from typing import List, Optional

from pydantic import BaseModel


class CalendarEvent(BaseModel):
    id: str
    title: str
    date: str
    startTime: str
    endTime: str
    description: str
    color: Optional[str] = None
    calendarName: Optional[str] = None
    readonly: bool = False


class CalendarEventUpsert(BaseModel):
    title: str
    date: str
    startTime: str
    endTime: str
    description: str = ""


class EventsResponse(BaseModel):
    events: List[CalendarEvent]


class DeleteResponse(BaseModel):
    success: bool


class WatchStartResponse(BaseModel):
    success: bool
    channel_id: Optional[str] = None
    resource_id: Optional[str] = None
    expiration: Optional[str] = None


class WatchStateResponse(BaseModel):
    active: bool
    channel_id: Optional[str] = None
    resource_id: Optional[str] = None
    expiration: Optional[str] = None


class OAuthStartResponse(BaseModel):
    authorization_url: str


class OAuthStatusResponse(BaseModel):
    connected: bool
