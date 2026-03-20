from fastapi import APIRouter, Depends

from ..auth.dependencies import get_current_user
from .schemas import MasterAgentChatRequest, MasterAgentChatResponse
from .service import run_master_agent_chat

router = APIRouter(prefix="/master-agent", tags=["master-agent"])


@router.post("/chat", response_model=MasterAgentChatResponse)
def chat(request: MasterAgentChatRequest, current_user: dict = Depends(get_current_user)):
    user_id = current_user.get("sub") if isinstance(current_user, dict) else None
    result = run_master_agent_chat(
        query=request.query,
        history=[message.model_dump() for message in request.history],
        user_id=user_id,
        model=request.model,
    )
    return MasterAgentChatResponse(**result)
