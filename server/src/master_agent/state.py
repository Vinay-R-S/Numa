"""Master-agent LangGraph state types (NUMA-106 P3, PLAN 16.3).

Extracted verbatim from master_agent/service.py; service.py re-exports these
names so existing import paths keep working.
"""
import operator
from typing import Annotated, List, Optional, Sequence, TypedDict


class TaskAgentState(TypedDict):
    messages: Annotated[Sequence[object], operator.add]
    user_query: str
    semantic_context: str
    mutated: bool


class MasterAgentState(TypedDict):
    query: str
    history: List[dict]
    user_id: str
    semantic_context: str
    route: str
    response: str
    success: bool
    delegated_to: Optional[str]
    refreshCalendar: bool
    refreshTasks: bool
    refreshSlack: bool
    refreshHealth: bool
    refreshGithub: bool
    refreshJournal: bool


class MasterToolState(TypedDict):
    messages: Annotated[Sequence[object], operator.add]
    user_query: str
    user_id: str
    semantic_context: str
