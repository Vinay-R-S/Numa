import logging

from fastapi import APIRouter, BackgroundTasks, Depends, Query

from ..auth.dependencies import get_current_user
from .schemas import (
    MasterAgentChatRequest,
    MasterAgentChatResponse,
    MasterAgentFetchLatestResponse,
)
from .service import run_master_agent_chat

router = APIRouter(prefix="/master-agent", tags=["master-agent"])
log = logging.getLogger(__name__)


def _run_fetch_latest_background(user_id: str | None) -> None:
    if not user_id:
        return

    try:
        from ..data_sync import fetch_latest_for_users

        fetch_latest_for_users([user_id])
    except Exception as exc:
        log.warning("Background fetch-latest failed for user %s: %s", user_id, exc)


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


@router.post("/fetch-latest", response_model=MasterAgentFetchLatestResponse)
def fetch_latest(
    background_tasks: BackgroundTasks,
    background: bool = Query(False),
    current_user: dict = Depends(get_current_user),
):
    user_id = current_user.get("sub") if isinstance(current_user, dict) else None
    if background:
        background_tasks.add_task(_run_fetch_latest_background, user_id)
        return MasterAgentFetchLatestResponse(
            ok=True,
            scope="selected_users_background",
            users=1 if user_id else 0,
            results=[],
            retention={"mode": "background"},
        )

    from ..data_sync import fetch_latest_for_users

    result = fetch_latest_for_users([user_id] if user_id else [])
    return MasterAgentFetchLatestResponse(**result)
