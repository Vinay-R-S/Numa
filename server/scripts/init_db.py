from pathlib import Path
import logging
import sys


SERVER_ROOT = Path(__file__).resolve().parents[1]
if str(SERVER_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVER_ROOT))

from src.core.db import init_db, verify_required_tables  # noqa: E402


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    init_db(raise_on_error=True)
    missing = verify_required_tables()
    if missing:
        raise SystemExit(f"Schema init finished, but tables are still missing: {', '.join(missing)}")
    print("Database schema created/migrated to Alembic head.")
