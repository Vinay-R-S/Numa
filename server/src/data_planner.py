"""Compatibility shim. Real module moved to src.core.data_planner in NUMA-102.

Import from src.core.data_planner in new code. This shim re-exports every public and
private name so existing import paths keep working during the transition.
"""
from src.core import data_planner as _module

globals().update(
    {k: v for k, v in vars(_module).items() if not k.startswith("__")}
)
