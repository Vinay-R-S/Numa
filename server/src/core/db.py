"""
Database access: connection pool, get_db() context manager, and the init_db()
entrypoint. Schema DDL lives entirely in Alembic migrations (NUMA-103).
"""
import os
import logging
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Optional

import psycopg2
from psycopg2.pool import ThreadedConnectionPool
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")
log = logging.getLogger(__name__)

# ── Connection pool ───────────────────────────────────────────────────────────
#
# All database operations share a process-wide connection pool instead of
# opening a fresh TCP connection on every call.  This eliminates the SSL
# handshake overhead and prevents connection exhaustion on Supabase.
#
# Existing code that calls ``_get_conn()`` / ``conn.close()`` continues to
# work unchanged — ``close()`` returns the connection to the pool rather
# than destroying it.  New code should prefer the ``get_db()`` context
# manager or call ``_put_conn(conn)`` in a finally block.

_pool: Optional[ThreadedConnectionPool] = None
_pool_lock = threading.Lock()

_DB_POOL_MIN = int(os.getenv("DB_POOL_MIN", "2"))
_DB_POOL_MAX = int(os.getenv("DB_POOL_MAX", "10"))


def _parse_database_url():
    """
    Parse DATABASE_URL manually to handle the '@' character inside the password.
    Format: postgresql://user:password@host:port/dbname
    """
    raw = os.environ["DATABASE_URL"].replace("postgresql://", "").replace("postgres://", "")

    at = raw.rfind("@")
    credentials, host_part = raw[:at], raw[at + 1:]

    colon = credentials.find(":")
    user, password = credentials[:colon], credentials[colon + 1:]

    host_and_port, dbname = host_part.split("/", 1)
    if ":" in host_and_port:
        host, port = host_and_port.rsplit(":", 1)
    else:
        host, port = host_and_port, "5432"

    return {
        "host": host,
        "port": int(port),
        "dbname": dbname,
        "user": user,
        "password": password,
        "sslmode": "require",
        "connect_timeout": 10,
    }


def _get_pool() -> ThreadedConnectionPool:
    """Return the process-wide connection pool, creating it on first call."""
    global _pool
    if _pool is not None and not _pool.closed:
        return _pool

    with _pool_lock:
        # Double-check after acquiring lock
        if _pool is not None and not _pool.closed:
            return _pool

        params = _parse_database_url()
        _pool = ThreadedConnectionPool(
            minconn=_DB_POOL_MIN,
            maxconn=_DB_POOL_MAX,
            **params,
        )
        log.info(
            "✓ Database connection pool created (min=%d, max=%d, host=%s)",
            _DB_POOL_MIN, _DB_POOL_MAX, params["host"],
        )
        return _pool


class _PooledConnection:
    """
    Thin wrapper that makes ``conn.close()`` return the connection to the
    pool instead of destroying it.  This preserves backward compatibility
    with all existing code that does ``conn = _get_conn(); ... conn.close()``.
    """

    def __init__(self, real_conn, pool: ThreadedConnectionPool):
        object.__setattr__(self, "_conn", real_conn)
        object.__setattr__(self, "_pool", pool)
        object.__setattr__(self, "_returned", False)

    def close(self):
        """Return connection to pool instead of closing it."""
        if not self._returned:
            self._returned = True
            try:
                # Reset connection state before returning to pool
                if not self._conn.closed:
                    self._conn.rollback()
                self._pool.putconn(self._conn)
            except Exception:
                pass

    def __getattr__(self, name):
        return getattr(self._conn, name)

    def __setattr__(self, name, value):
        if name in {"_conn", "_pool", "_returned"}:
            object.__setattr__(self, name, value)
        else:
            setattr(self._conn, name, value)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


def _get_conn():
    """
    Get a database connection from the pool.

    The returned connection is wrapped so that calling ``.close()`` returns
    it to the pool rather than destroying it.  This makes this function a
    drop-in replacement for the old raw ``psycopg2.connect()`` call.
    """
    pool = _get_pool()
    real_conn = pool.getconn()
    return _PooledConnection(real_conn, pool)


def _put_conn(conn) -> None:
    """Explicitly return a pooled connection (alternative to conn.close())."""
    if isinstance(conn, _PooledConnection):
        conn.close()
    else:
        try:
            _get_pool().putconn(conn)
        except Exception:
            pass


@contextmanager
def get_db():
    """Context manager for database connections — recommended for new code.

    Usage::

        from src.db import get_db
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute("SELECT 1")
    """
    conn = _get_conn()
    try:
        yield conn
    finally:
        conn.close()


def row_to_dict(cursor, row) -> dict:
    """Map a single DB row to a dict using the cursor description.

    Shared helper that replaces the per-feature _row_to_dict copies (PLAN 10).
    """
    if row is None:
        return {}
    cols = [c[0] for c in cursor.description]
    return dict(zip(cols, row))


# ── Schema (Alembic is the single source of truth) ──────────────────
# All DDL lives in migrations/versions/*.py. init_db() runs `alembic upgrade
# head`; there is no inline DDL here (NUMA-103).

REQUIRED_TABLES = (
    "profiles",
    "tasks",
    "cal_calendars",
    "cal_events",
    "cal_attendees",
    "cal_watch_channels",
    "user_ai_settings",
    "journal_entries",
    "github_auth",
    "github_repositories",
    "github_commits",
    "github_resource_snapshots",
    "health_snapshots",
    "health_intraday_snapshots",
)


def _missing_required_tables(cur) -> list[str]:
    cur.execute(
        """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
          AND table_name = ANY(%s)
        """,
        (list(REQUIRED_TABLES),),
    )
    existing = {row[0] for row in cur.fetchall()}
    return [table for table in REQUIRED_TABLES if table not in existing]


def verify_required_tables() -> list[str]:
    """Return any required public tables that are still missing."""
    conn = _get_conn()
    try:
        cur = conn.cursor()
        try:
            return _missing_required_tables(cur)
        finally:
            cur.close()
    finally:
        conn.close()


# ── Entrypoint ───────────────────────────────────

_SERVER_ROOT = Path(__file__).resolve().parents[2]


def _alembic_config():
    from alembic.config import Config

    cfg = Config(str(_SERVER_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(_SERVER_ROOT / "migrations"))
    # We are embedding Alembic, so env.py must not apply alembic.ini's logging
    # config: it pins the root logger at WARNING for the rest of the process.
    cfg.attributes["configure_logger"] = False
    return cfg


def init_db(*, raise_on_error: bool = False) -> None:
    """Create or migrate the database schema by running Alembic to head.

    Alembic is the single source of schema truth (NUMA-103). On a clean database
    the baseline migration builds the full schema; on an existing database only
    pending migrations run. Idempotent and safe to call on every startup.

    The post-upgrade verification restores the fail-fast the inline-DDL version
    had: `upgrade head` is a no-op on a database whose revision is already
    stamped at head, so a schema that was partially restored, manually dropped
    or `alembic stamp`ed onto an empty database would otherwise boot green and
    then raise UndefinedTable on every request instead of at startup.
    """
    try:
        from alembic import command

        command.upgrade(_alembic_config(), "head")

        missing = verify_required_tables()
        if missing:
            raise RuntimeError(
                "Alembic is at head but required tables are missing: "
                f"{', '.join(missing)}. The database schema and the migration "
                "history disagree; resolve before serving traffic."
            )

        log.info("Database schema migrated to Alembic head.")
    except Exception:
        log.exception("Database init (alembic upgrade head) failed")
        if raise_on_error:
            raise
