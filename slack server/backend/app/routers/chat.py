"""Natural language chat / agent endpoint."""
from datetime import date
from fastapi import APIRouter, HTTPException, Depends

from app.auth import get_current_user
from app.database import get_supabase
from app.models import ChatRequest, ChatResponse, UserOut
from app.intent_parser import parse_intent
from app.slack_action_router import SlackActionRouter

router = APIRouter(prefix="/chat", tags=["chat"])


def _bump_commands_used(user_id: str):
    try:
        today = date.today().isoformat()
        db = get_supabase()
        resp = (
            db.table("analytics")
            .select("id,commands_used")
            .eq("user_id", user_id)
            .eq("period_date", today)
            .limit(1)
            .execute()
        )
        if resp.data:
            row = resp.data[0]
            db.table("analytics").update(
                {"commands_used": (row.get("commands_used") or 0) + 1}
            ).eq("id", row["id"]).execute()
        else:
            db.table("analytics").insert(
                {"user_id": user_id, "period_date": today, "commands_used": 1}
            ).execute()
    except Exception:
        pass  # never block the response over an analytics write


@router.post("", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    current_user: UserOut = Depends(get_current_user),
):
    try:
        intent_data = parse_intent(request.message)
        action_router = SlackActionRouter()
        result = action_router.execute(intent_data, user_id=current_user.id)

        if result.get("ok"):
            text_response = result.get("message") or str(result)
            _bump_commands_used(current_user.id)
        else:
            text_response = f"Error: {result.get('error')}"

        return ChatResponse(
            response=text_response,
            intent=intent_data.intent,
            debug_info=result,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
