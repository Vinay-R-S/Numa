"""
Clean all Python cache files from the project.
Usage: python c.py
"""
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))

CACHE_DIRS = {"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"}
CACHE_FILES = {".pyc", ".pyo", ".pyd"}
EXTRA_PATTERNS = {"*.egg-info"}

removed_dirs = 0
removed_files = 0

for root, dirs, files in os.walk(ROOT, topdown=False):
    if ".git" in root or "node_modules" in root or ".next" in root:
        continue

    for f in files:
        ext = os.path.splitext(f)[1].lower()
        if ext in CACHE_FILES:
            path = os.path.join(root, f)
            os.remove(path)
            print(f"  del  {os.path.relpath(path, ROOT)}")
            removed_files += 1

    for d in dirs:
        if d in CACHE_DIRS or d.endswith(".egg-info"):
            path = os.path.join(root, d)
            shutil.rmtree(path, ignore_errors=True)
            print(f"  rm   {os.path.relpath(path, ROOT)}/")
            removed_dirs += 1

print(f"\nCleaned {removed_dirs} cache dirs, {removed_files} cache files.")
