"""Slack messages listing."""
from fastapi import APIRouter, Depends, Query

from app.auth import get_current_user
from app.database import get_supabase
from app.models import UserOut, MessageOut

router = APIRouter(prefix="/messages", tags=["messages"])


@router.get("", response_model=list[MessageOut])
async def list_messages(
    limit: int = Query(50, le=200),
    channel_id: str | None = None,
    relevant_only: bool = Query(False, description="Return only messages that mention the user or are @channel/@here broadcasts"),
    current_user: UserOut = Depends(get_current_user),
):
    db = get_supabase()
    uid = current_user.slack_user_id

    if relevant_only:
        # Messages from anyone that directly mention this user or are broadcasts
        q = (
            db.table("messages")
            .select("*")
            .or_(
                f"text.like.%<@{uid}>%,"
                "text.like.%<!channel>%,"
                "text.like.%<!here>%,"
                "text.like.%<!everyone>%"
            )
        )
    else:
        # Default: messages sent by the current user
        q = db.table("messages").select("*").eq("slack_user_id", uid)

    if channel_id:
        q = q.eq("channel_id", channel_id)

    resp = q.order("created_at", desc=True).limit(limit).execute()
    return [MessageOut(**m) for m in (resp.data or [])]
