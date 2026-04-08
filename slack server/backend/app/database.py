from supabase import create_client, Client
from app.config import settings

_client: Client | None = None


def get_supabase() -> Client:
    """
    Returns a singleton Supabase client using the service_role key.
    This client bypasses Row Level Security and is safe only for server-side use.
    """
    global _client
    if _client is None:
        _client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)
    return _client


def get_or_create_channel(channel_id: str, channel_name: str | None, team_id: str | None) -> str:
    """Get channel UUID from channels table, inserting it when missing."""
    db = get_supabase()
    existing = (
        db.table("channels")
        .select("id")
        .eq("channel_id", channel_id)
        .limit(1)
        .execute()
    )
    if existing.data:
        return existing.data[0]["id"]

    inserted = (
        db.table("channels")
        .insert({
            "channel_id": channel_id,
            "channel_name": channel_name,
            "team_id": team_id,
        })
        .execute()
    )
    return inserted.data[0]["id"]


def upsert_user_token(
    user_id: str,
    access_token: str,
    token_type: str | None = None,
    expires_at: str | None = None,
) -> None:
    """Persist OAuth token material in user_tokens table."""
    db = get_supabase()
    existing = (
        db.table("user_tokens")
        .select("id")
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )

    payload = {
        "access_token": access_token,
        "token_type": token_type,
        "expires_at": expires_at,
    }

    if existing.data:
        db.table("user_tokens").update(payload).eq("id", existing.data[0]["id"]).execute()
    else:
        db.table("user_tokens").insert({"user_id": user_id, **payload}).execute()


def save_extracted_intelligence(
    user_id: str,
    type: str,
    content: str,
    metadata: dict | None = None,
    importance: int = 1,
) -> None:
    """Store extracted insights from message analysis."""
    get_supabase().table("extracted_intelligence").insert(
        {
            "user_id": user_id,
            "type": type,
            "content": content,
            "metadata": metadata or {},
            "importance": importance,
        }
    ).execute()
