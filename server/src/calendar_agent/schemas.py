from typing import List

from pydantic import BaseModel, Field


class ChatHistoryMessage(BaseModel):
    role: str
    content: str


class AgentChatRequest(BaseModel):
    query: str = Field(..., description="User query for the calendar agent")
    history: List[ChatHistoryMessage] = Field(
        default_factory=list, description="Prior conversation turns"
    )


class AgentChatResponse(BaseModel):
    response: str
    success: bool
    refreshCalendar: bool = False
