"""Auth data-access layer (NUMA-110, PLAN 6/18/21). SQL only."""
from ..core.base import BaseRepository
from ..core.db import get_db


class AuthRepository(BaseRepository):
    def slack_auth_exists(self, user_id: str) -> bool:
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT 1 FROM public.slack_auth WHERE user_id = %s LIMIT 1",
                (user_id,),
            )
            return cur.fetchone() is not None


auth_repository = AuthRepository()
