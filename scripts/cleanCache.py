import shutil
import os
from pathlib import Path

def remove_pycache(root_dir="."):
    """Recursively deletes all __pycache__ directories from the root_dir."""
    root = Path(root_dir).resolve()
    print(f"Searching for __pycache__ in: {root}")
    
    deleted_count = 0
    
    # rglob recursively finds all directories named __pycache__
    for folder in root.rglob("__pycache__"):
        if folder.is_dir():
            try:
                shutil.rmtree(folder)
                print(f"Successfully deleted: {folder.relative_to(root)}")
                deleted_count += 1
            except Exception as e:
                print(f"Error deleting {folder}: {e}")

    print(f"\nCleanup finished. Removed {deleted_count} directories.")

if __name__ == "__main__":
    # Runs in the current directory of the script
    remove_pycache()
