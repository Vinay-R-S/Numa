from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, Field


class JournalEntryCreate(BaseModel):
    title: str = ""
    content: str = ""
    mood: Optional[str] = Field(None, pattern="^(great|good|okay|bad|terrible)$")
    entry_date: Optional[date] = None
    tags: list[str] = Field(default_factory=list)


class JournalEntryUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    mood: Optional[str] = Field(None, pattern="^(great|good|okay|bad|terrible)$")
    tags: Optional[list[str]] = None


class JournalEntryOut(BaseModel):
    id: str
    user_id: str
    title: str
    content: str
    mood: Optional[str] = None
    entry_date: date
    tags: list[str] = Field(default_factory=list)
    ai_summary: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class JournalListResponse(BaseModel):
    entries: list[JournalEntryOut]
    total: int


class JournalSummaryRequest(BaseModel):
    entry_date: Optional[date] = None


class JournalSummaryResponse(BaseModel):
    summary: str
    entry_date: date
