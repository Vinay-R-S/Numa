"""
Replace em dashes and en dashes with normal hyphens across project files.
Only touches project source files - skips packages, models, and dependencies.
Usage: python d.py
"""
import os

ROOT = os.path.dirname(os.path.abspath(__file__))

PROJECT_DIRS = {"client/src", "server/src", "server/main.py", "docs"}
EXTS = {".tsx", ".ts", ".py", ".md", ".css", ".json", ".html", ".jsx", ".js"}
SKIP = {
    ".git", "node_modules", ".next", "__pycache__", ".venv", "venv", "env",
    "models", "dist", "build", ".egg-info", "package-lock.json",
}

EM = "\u2014"
EN = "\u2013"
REPLACE = "-"


def should_skip(path: str) -> bool:
    parts = path.replace("\\", "/").split("/")
    return any(p in SKIP for p in parts)


count = 0
files_fixed = 0

for root, dirs, files in os.walk(ROOT):
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
        print(f"  Fixed {n} dash(es) in {os.path.relpath(path, ROOT)}")
        count += n
        files_fixed += 1

if count == 0:
    print("No em/en dashes found. Project is clean!")
else:
    print(f"\nReplaced {count} dashes across {files_fixed} files.")
