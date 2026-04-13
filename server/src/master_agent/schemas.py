from typing import List, Optional

from pydantic import BaseModel, Field


class MasterAgentHistoryMessage(BaseModel):
    role: str
    content: str


class MasterAgentChatRequest(BaseModel):
    query: str = Field(..., description="User query for the master agent")
    history: List[MasterAgentHistoryMessage] = Field(
        default_factory=list,
        description="Prior conversation turns",
    )
    model: Optional[str] = Field(default=None, description="Optional model preset (70b or 8b)")


class MasterAgentChatResponse(BaseModel):
    response: str
    success: bool
    delegated_to: Optional[str] = None
    refreshCalendar: bool = False
    refreshTasks: bool = False
    refreshSlack: bool = False
