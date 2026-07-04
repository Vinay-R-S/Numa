"""AI settings data-access layer (NUMA-121, PLAN 6/18/21). SQL only."""
from typing import Dict, Optional

from ..core.base import BaseRepository
from ..core.db import get_db, row_to_dict

_RETURNING = "RETURNING provider, model_id, encrypted_api_key, ollama_base_url, temperature"


class AISettingsRepository(BaseRepository):
    def get(self, user_id: str) -> Optional[Dict]:
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT provider, model_id, encrypted_api_key, ollama_base_url, temperature "
                "FROM public.user_ai_settings WHERE user_id = %s",
                (user_id,),
            )
            row = cur.fetchone()
            return row_to_dict(cur, row) if row else None

    def upsert(
        self, user_id: str, provider: str, model_id: str,
        encrypted: Optional[str], ollama_base_url: Optional[str],
        temperature: float, include_key: bool,
    ) -> Dict:
        with get_db() as conn:
            cur = conn.cursor()
            try:
                if include_key:
                    cur.execute(
                        "INSERT INTO public.user_ai_settings "
                        "(user_id, provider, model_id, encrypted_api_key, ollama_base_url, temperature) "
                        "VALUES (%s, %s, %s, %s, %s, %s) "
                        "ON CONFLICT (user_id) DO UPDATE SET "
                        "    provider = EXCLUDED.provider, "
                        "    model_id = EXCLUDED.model_id, "
                        "    encrypted_api_key = EXCLUDED.encrypted_api_key, "
                        "    ollama_base_url = EXCLUDED.ollama_base_url, "
                        "    temperature = EXCLUDED.temperature, "
                        "    updated_at = NOW() " + _RETURNING,
                        (user_id, provider, model_id, encrypted, ollama_base_url, temperature),
                    )
                else:
                    cur.execute(
                        "INSERT INTO public.user_ai_settings "
                        "(user_id, provider, model_id, ollama_base_url, temperature) "
                        "VALUES (%s, %s, %s, %s, %s) "
                        "ON CONFLICT (user_id) DO UPDATE SET "
                        "    provider = EXCLUDED.provider, "
                        "    model_id = EXCLUDED.model_id, "
                        "    ollama_base_url = EXCLUDED.ollama_base_url, "
                        "    temperature = EXCLUDED.temperature, "
                        "    updated_at = NOW() " + _RETURNING,
                        (user_id, provider, model_id, ollama_base_url, temperature),
                    )
                result = row_to_dict(cur, cur.fetchone())
                conn.commit()
                return result
            except Exception:
                conn.rollback()
                raise

    def delete(self, user_id: str) -> None:
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM public.user_ai_settings WHERE user_id = %s", (user_id,))
            conn.commit()


ai_settings_repository = AISettingsRepository()
