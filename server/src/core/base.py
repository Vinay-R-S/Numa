"""Base classes for the layered feature architecture (NUMA-102, PLAN 21).

Additive scaffolding. Feature repositories/services/clients adopt these as they
are refactored; nothing is forced to use them yet.
"""
import logging

from src.core.db import get_db, row_to_dict


class BaseRepository:
    """SQL-only data access. Subclasses add table-specific methods."""

    def _query(self, sql: str, params: tuple = ()) -> list[dict]:
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute(sql, params)
            rows = cur.fetchall()
            return [row_to_dict(cur, row) for row in rows]

    def _execute(self, sql: str, params: tuple = ()) -> int:
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute(sql, params)
            conn.commit()
            return cur.rowcount


class BaseService:
    """Business logic and orchestration. Holds injected repositories/clients."""

    def __init__(self) -> None:
        self.log = logging.getLogger(self.__class__.__module__)


class BaseClient:
    """External API wrapper base: timeout/retry/auth normalization."""

    def __init__(self, base_url: str = "", timeout: float = 15.0) -> None:
        self.base_url = base_url
        self.timeout = timeout
        self.log = logging.getLogger(self.__class__.__module__)
