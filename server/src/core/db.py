"""
Database access: connection pool, get_db() context manager, and the init_db()
entrypoint. Schema DDL lives entirely in Alembic migrations (NUMA-103).
"""
import asyncio
import os
import logging
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Optional
from urllib.parse import unquote, urlsplit

import psycopg2
from psycopg2.pool import PoolError, ThreadedConnectionPool
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
# work unchanged - ``close()`` returns the connection to the pool rather
# than destroying it.  New code should prefer the ``get_db()`` context
# manager or call ``_put_conn(conn)`` in a finally block.

_pool: Optional[ThreadedConnectionPool] = None
_pool_lock = threading.Lock()

_DB_POOL_MIN = int(os.getenv("DB_POOL_MIN", "2"))
_DB_POOL_MAX = int(os.getenv("DB_POOL_MAX", "10"))

# Callers queue for a connection instead of failing on the spot (NUMA-135 P6,
# PLAN 7). Nearly every route in this app is a sync `def`, so Starlette runs it
# in anyio's threadpool, which holds 40 workers by default - four times the
# pool. psycopg2's getconn does not wait: the 11th concurrent request raised
# `PoolError: connection pool exhausted`, nothing catches it, and the caller got
# a 500 while ten perfectly healthy connections were a few milliseconds from
# being free. The semaphore turns that into a bounded wait.
_DB_POOL_TIMEOUT = float(os.getenv("DB_POOL_TIMEOUT", "10"))
_pool_slots: Optional[threading.BoundedSemaphore] = None

# Set by close_pool(). Shutdown bounds how long it waits for a background job to
# finish, so a slow job can still call get_db() after the pool is gone; without
# this flag `_get_pool()` would happily open a brand-new pool against Postgres
# after shutdown, which is the "too many clients" leak close_pool() exists to
# prevent (NUMA-142 P6 review).
_shutting_down = False


def _encode_userinfo(raw: str) -> str:
    """Percent-encode the userinfo of a DSN so `urlsplit` reads it correctly.

    Only characters that would otherwise end the authority are encoded, and only
    inside the userinfo, so a password already written as `p%40ss` is untouched
    and still decodes to `p@ss`.
    """
    scheme, sep, rest = raw.partition("://")
    if not sep:
        return raw

    # Split on the last "/" that precedes the "@", not the first: a "/" inside
    # the password would otherwise end the authority before `rpartition("@")`
    # ever ran, and the URL came back unchanged to fail later as a non-numeric
    # port (NUMA-142 P6 review). Generated passwords contain "/" routinely.
    at_index = rest.find("@")
    if at_index == -1:
        return raw

    boundary = rest.find("/", at_index)
    authority = rest if boundary == -1 else rest[:boundary]
    slash = "" if boundary == -1 else "/"
    tail = "" if boundary == -1 else rest[boundary + 1:]

    userinfo, at, hostport = authority.rpartition("@")
    if not at:
        return raw

    encoded = userinfo
    for char, replacement in (("#", "%23"), ("?", "%3F"), ("/", "%2F")):
        encoded = encoded.replace(char, replacement)

    return f"{scheme}://{encoded}@{hostport}{slash}{tail}"


def _parse_database_url():
    """Split DATABASE_URL into psycopg2 connection parameters.

    Hand-rolled string slicing got three common URL shapes wrong (NUMA-142 P6,
    PLAN 7):

    - the query string was never removed, so the `?sslmode=require` form
      Supabase hands out (and the `?pgbouncer=true` its pooler adds) produced
      `dbname="postgres?sslmode=require"` and killed the boot with
      `database "postgres?sslmode=require" does not exist`;
    - the password was never percent-decoded, so one stored as `p%40ss` was
      sent literally and authentication failed;
    - a URL with no password has no colon in its userinfo, so `find(":")`
      returned -1 and the slices produced a silently wrong user and password
      rather than an error.

    `urlsplit` splits userinfo on the last `@`, which is what the old `rfind`
    was there for, so an unencoded `@` inside a password still works.

    libpq parameters in the query string are deliberately not forwarded:
    `sslmode` is pinned to `require` as policy, and honouring a URL that asked
    to turn TLS off would be a downgrade this function should not grant.
    """
    raw = os.environ["DATABASE_URL"].strip()

    # A literal `#` or `?` in the password is legal in a URL people actually
    # paste, and `urlsplit` would read it as the start of the fragment or query
    # and then report a missing database name. Percent-encode the userinfo
    # before splitting so those keep working, exactly as they did under the
    # hand-rolled `rfind("@")` this replaced (NUMA-142 P6 review).
    parts = urlsplit(_encode_userinfo(raw))

    if parts.scheme not in ("postgresql", "postgres"):
        raise ValueError(f"DATABASE_URL has an unsupported scheme: {parts.scheme!r}")

    dbname = parts.path.lstrip("/")
    if not dbname:
        raise ValueError("DATABASE_URL is missing a database name")

    host = parts.hostname
    if not host:
        raise ValueError("DATABASE_URL is missing a host")

    try:
        port = parts.port or 5432
    except ValueError as exc:
        raise ValueError("DATABASE_URL has a non-numeric port") from exc

    # urlsplit leaves these percent-encoded; psycopg2 wants the decoded value.
    user = unquote(parts.username or "")
    password = unquote(parts.password or "")

    return {
        "host": host,
        "port": port,
        "dbname": unquote(dbname),
        "user": user,
        "password": password,
        "sslmode": "require",
        "connect_timeout": 10,
    }


def _get_pool() -> ThreadedConnectionPool:
    """Return the process-wide connection pool, creating it on first call."""
    global _pool, _pool_slots
    if _pool is not None and not _pool.closed:
        return _pool

    with _pool_lock:
        # Double-check after acquiring lock
        if _pool is not None and not _pool.closed:
            return _pool

        if _shutting_down:
            raise PoolError("The database pool is closed: the app is shutting down")

        params = _parse_database_url()
        _pool = ThreadedConnectionPool(
            minconn=_DB_POOL_MIN,
            maxconn=_DB_POOL_MAX,
            **params,
        )
        # Recreated with the pool, so a pool rebuilt after a close does not
        # inherit slots that were counted against the old one.
        _pool_slots = threading.BoundedSemaphore(_DB_POOL_MAX)
        log.info(
            "✓ Database connection pool created (min=%d, max=%d, wait=%.1fs, host=%s)",
            _DB_POOL_MIN, _DB_POOL_MAX, _DB_POOL_TIMEOUT, params["host"],
        )
        return _pool


class _PooledConnection:
    """
    Thin wrapper that makes ``conn.close()`` return the connection to the
    pool instead of destroying it.  This preserves backward compatibility
    with all existing code that does ``conn = _get_conn(); ... conn.close()``.
    """

    def __init__(self, real_conn, pool: ThreadedConnectionPool, slot=None):
        object.__setattr__(self, "_conn", real_conn)
        object.__setattr__(self, "_pool", pool)
        object.__setattr__(self, "_slot", slot)
        object.__setattr__(self, "_returned", False)

    def close(self):
        """Return connection to pool instead of closing it."""
        if self._returned:
            return

        self._returned = True
        try:
            # Reset connection state before returning to pool
            if not self._conn.closed:
                self._conn.rollback()
            # psycopg2 refuses putconn on a closed pool, and a request still in
            # flight when close_pool() ran is the normal way to get here: its
            # connection is already closed, so there is nothing to hand back.
            if not self._pool.closed:
                self._pool.putconn(self._conn)
        except Exception:
            # Swallowed but no longer silent: a connection that cannot be
            # handed back is a pool slot gone for the life of the process, and
            # the old bare `pass` made that invisible.
            log.warning("Failed to return a connection to the pool", exc_info=True)
        finally:
            # Always, even when putconn failed: the slot counts callers, not
            # connections, and holding it back would shrink the pool twice.
            if self._slot is not None:
                self._slot.release()

    def __getattr__(self, name):
        return getattr(self._conn, name)

    def __setattr__(self, name, value):
        if name in {"_conn", "_pool", "_slot", "_returned"}:
            object.__setattr__(self, name, value)
        else:
            setattr(self._conn, name, value)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


def _acquire_timeout() -> float:
    """How long this caller may wait for a free connection.

    Zero on the event loop. Sync routes run in a worker thread, where a wait
    costs that one request; an `async def` route that touches the DB inline
    (`/slack/events` does, through `_delete_slack_message_by_ts`) would block
    the loop, so a queue there stalls every request in the process rather than
    the one that has to wait. Those callers keep the old fail-fast behaviour.
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return _DB_POOL_TIMEOUT
    return 0.0


def _get_conn():
    """
    Get a database connection from the pool.

    The returned connection is wrapped so that calling ``.close()`` returns
    it to the pool rather than destroying it.  This makes this function a
    drop-in replacement for the old raw ``psycopg2.connect()`` call.

    Waits up to ``DB_POOL_TIMEOUT`` seconds for a free slot rather than
    failing the moment the pool is full (NUMA-135).
    """
    pool = _get_pool()
    slot = _pool_slots
    timeout = _acquire_timeout()
    if slot is not None and not slot.acquire(timeout=timeout):
        waited = (
            f"Timed out after {timeout:.1f}s waiting for a database connection"
            if timeout
            else "No database connection free, and this caller runs on the event "
                 "loop, where waiting would stall every other request"
        )
        raise PoolError(
            f"{waited}; all {_DB_POOL_MAX} are in use. Raise DB_POOL_MAX, or "
            f"look for a caller holding one too long."
        )

    try:
        real_conn = pool.getconn()
    except Exception:
        # The slot is only meaningful while a connection is held.
        if slot is not None:
            slot.release()
        raise

    return _PooledConnection(real_conn, pool, slot)


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
    """Context manager for database connections - recommended for new code.

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


def close_pool() -> None:
    """Close every pooled connection. Called from the lifespan shutdown.

    Nothing closed the pool before, so a restart left its sockets for Postgres
    to time out - which on a small connection allowance is the difference
    between restarting cleanly and restarting into "too many clients".
    Idempotent. A later `_get_pool()` refuses rather than rebuilding: a
    background job that outran the bounded shutdown wait used to open a fresh
    pool after the app had gone (NUMA-142 P6 review). `reopen_pool()` lifts the
    flag for a process that shuts a pool and keeps running, such as a test.
    """
    global _pool, _pool_slots, _shutting_down
    with _pool_lock:
        _shutting_down = True
        pool = _pool
        _pool = None
        _pool_slots = None

    if pool is None or pool.closed:
        return

    try:
        pool.closeall()
        log.info("Database connection pool closed.")
    except Exception:
        log.warning("Failed to close the database connection pool", exc_info=True)


def reopen_pool() -> None:
    """Allow the pool to be rebuilt after `close_pool()`. For tests and scripts."""
    global _shutting_down
    with _pool_lock:
        _shutting_down = False


@contextmanager
def using(conn=None):
    """Yield the caller's connection, or a pooled one this closes itself.

    Lets a repository method be called both standalone and inside a caller's
    existing transaction. Four modules hand-rolled their own `health_snapshots`
    SQL precisely because the repository always opened its own connection, and
    they batch many statements on one (`dashboard` runs 18, and its per-query
    rollback depends on sharing them). Borrowing a connection is never closed
    here: the owner opened it and the owner closes it (NUMA-143 P7, PLAN 10).
    """
    if conn is not None:
        yield conn
        return

    with get_db() as owned:
        yield owned


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
