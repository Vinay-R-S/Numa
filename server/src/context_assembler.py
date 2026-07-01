"""Compatibility shim. Real module moved to src.core.context_assembler in NUMA-102.

Import from src.core.context_assembler in new code. This shim re-exports every public and
private name so existing import paths keep working during the transition.
"""
from src.core import context_assembler as _module

globals().update(
    {k: v for k, v in vars(_module).items() if not k.startswith("__")}
)
