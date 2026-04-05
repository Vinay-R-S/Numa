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
