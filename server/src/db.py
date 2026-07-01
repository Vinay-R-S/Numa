"""Compatibility shim. Real module moved to src.core.db in NUMA-102.

Import from src.core.db in new code. This shim re-exports every public and
private name so existing import paths keep working during the transition.
"""
from src.core import db as _module

globals().update(
    {k: v for k, v in vars(_module).items() if not k.startswith("__")}
)
