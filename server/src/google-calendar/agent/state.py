"""
Agent State Definition
Defines the state structure for the LangGraph agent
"""

from typing import TypedDict, Annotated, Sequence
from langchain_core.messages import BaseMessage
import operator


class AgentState(TypedDict):
    """
    State for the agent graph
    
    Attributes:
        messages: List of conversation messages
        user_query: Original user query
    """
    # Messages will be accumulated (appended) using the operator.add reducer
    messages: Annotated[Sequence[BaseMessage], operator.add]
    user_query: str
