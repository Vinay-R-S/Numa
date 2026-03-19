from fastapi import APIRouter, Depends

from ..auth.dependencies import get_current_user
from .schemas import AgentChatRequest, AgentChatResponse
from .service import run_agent_chat

router = APIRouter(prefix="/agent", tags=["agent"])


@router.post("/chat", response_model=AgentChatResponse)
def chat(request: AgentChatRequest, current_user: dict = Depends(get_current_user)):
    user_id = current_user.get("sub") if isinstance(current_user, dict) else None
    result = run_agent_chat(
        query=request.query,
        history=[message.model_dump() for message in request.history],
        user_id=user_id,
    )
    return AgentChatResponse(**result)
