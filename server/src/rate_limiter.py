"""Compatibility shim. Real module moved to src.core.rate_limiter in NUMA-102.

Import from src.core.rate_limiter in new code. This shim re-exports every public and
private name so existing import paths keep working during the transition.
"""
from src.core import rate_limiter as _module

globals().update(
    {k: v for k, v in vars(_module).items() if not k.startswith("__")}
)
