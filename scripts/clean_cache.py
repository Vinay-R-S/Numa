"""
Remove Python cache artifacts from the project.
Usage: python scripts/clean_cache.py
"""
import os
import shutil

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CACHE_DIRS = {"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"}
CACHE_FILE_EXTS = {".pyc", ".pyo", ".pyd"}
SKIP_DIRS = {".git", "node_modules", ".next", ".venv", "venv", "env"}

removed_dirs = 0
removed_files = 0

for root, dirs, files in os.walk(PROJECT_ROOT, topdown=False):
    if set(root.replace("\\", "/").split("/")) & SKIP_DIRS:
        continue

    for f in files:
        if os.path.splitext(f)[1].lower() in CACHE_FILE_EXTS:
            path = os.path.join(root, f)
            os.remove(path)
            print(f"  del  {os.path.relpath(path, PROJECT_ROOT)}")
            removed_files += 1

    for d in dirs:
        if d in CACHE_DIRS or d.endswith(".egg-info"):
            path = os.path.join(root, d)
            shutil.rmtree(path, ignore_errors=True)
            print(f"  rm   {os.path.relpath(path, PROJECT_ROOT)}/")
            removed_dirs += 1

print(f"\nCleaned {removed_dirs} cache dirs, {removed_files} cache files.")
