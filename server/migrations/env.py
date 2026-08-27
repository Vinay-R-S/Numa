"""
Alembic env.py - configured to read DATABASE_URL from server/.env
and run raw-SQL migrations via psycopg2 (no SQLAlchemy models needed).
"""
import logging
import os
from pathlib import Path
from logging.config import fileConfig

from alembic import context
from dotenv import load_dotenv
from sqlalchemy import create_engine, pool

# ── Load the same .env that the FastAPI server uses ──────────────────────────
SERVER_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(SERVER_ROOT / ".env")

# Alembic Config object (provides access to alembic.ini values)
config = context.config

# Override sqlalchemy.url from the environment variable
db_url = os.environ.get("DATABASE_URL", "")
if db_url:
    # SQLAlchemy requires postgresql:// prefix (not postgres://)
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
    config.set_main_option("sqlalchemy.url", db_url)

# Logging setup from alembic.ini, but only when Alembic owns the process.
#
# `disable_existing_loggers=False` spares already-created loggers, yet fileConfig
# still rewrites the ROOT logger's handlers and level (alembic.ini pins it to
# WARNING). Running `alembic upgrade head` programmatically - init_db() does it
# on every server startup, and scripts/init_db.py right after basicConfig -
# therefore pins the whole process at WARNING and swallows the caller's INFO
# output, including init_db()'s own success line.
#
# An embedded caller says so by setting `configure_logger = False` on the Config
# it passes in (core.db._alembic_config does); the root-handler check is the
# fallback for any other embedder. The CLI sets neither and configures as usual.
_owns_logging = config.attributes.get("configure_logger", True)

if _owns_logging and config.config_file_name is not None and not logging.getLogger().handlers:
    fileConfig(config.config_file_name, disable_existing_loggers=False)

# No declarative metadata - we use raw SQL migrations
target_metadata = None


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode - generates SQL script."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def _parse_database_url():
    """Same parsing logic as src/db.py to handle '@' in passwords."""
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
        "host": host, "port": int(port), "dbname": dbname,
        "user": user, "password": password,
        "sslmode": "require", "connect_timeout": 10,
    }


def run_migrations_online() -> None:
    """Run migrations in 'online' mode using a properly constructed SQLAlchemy engine."""
    from urllib.parse import quote_plus
    from sqlalchemy import create_engine

    params = _parse_database_url()
    # Build a properly URL-encoded connection string
    encoded_password = quote_plus(params["password"])
    url = (
        f"postgresql://{params['user']}:{encoded_password}"
        f"@{params['host']}:{params['port']}/{params['dbname']}"
        f"?sslmode={params['sslmode']}"
    )

    engine = create_engine(url, pool_pre_ping=True)

    with engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
