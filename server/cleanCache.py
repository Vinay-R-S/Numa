"""Remove all __pycache__ directories under the server folder."""
import shutil
from pathlib import Path

root = Path(__file__).parent
removed = 0

for cache in root.rglob("__pycache__"):
    shutil.rmtree(cache)
    print(f"Removed: {cache.relative_to(root)}")
    removed += 1

print(f"\nDone — {removed} cache folder(s) removed.")
