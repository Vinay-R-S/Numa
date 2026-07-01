"""
Replace em dashes and en dashes with normal hyphens across project source files.
Skips packages, virtualenvs, build output, and dependencies.
Usage: python scripts/normalize_dashes.py
"""
import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXTS = {".tsx", ".ts", ".py", ".md", ".css", ".json", ".html", ".jsx", ".js"}
SKIP = {
    ".git", "node_modules", ".next", "__pycache__", ".venv", "venv", "env",
    "models", "dist", "build", ".egg-info", "package-lock.json",
}

EM = "\u2014"  # em dash
EN = "\u2013"  # en dash
REPLACE = "-"


def should_skip(path: str) -> bool:
    parts = path.replace("\\", "/").split("/")
    return any(p in SKIP for p in parts)


count = 0
files_fixed = 0

for root, dirs, files in os.walk(PROJECT_ROOT):
    dirs[:] = [d for d in dirs if d not in SKIP]
    if should_skip(root):
        continue

    for f in files:
        if os.path.splitext(f)[1].lower() not in EXTS:
            continue
        if f in SKIP:
            continue

        path = os.path.join(root, f)
        try:
            text = open(path, encoding="utf-8").read()
        except Exception:
            continue

        n = text.count(EM) + text.count(EN)
        if n == 0:
            continue

        new = text.replace(EM, REPLACE).replace(EN, REPLACE)
        open(path, "w", encoding="utf-8").write(new)
        print(f"  Fixed {n} dash(es) in {os.path.relpath(path, PROJECT_ROOT)}")
        count += n
        files_fixed += 1

if count == 0:
    print("No em/en dashes found. Project is clean!")
else:
    print(f"\nReplaced {count} dashes across {files_fixed} files.")
