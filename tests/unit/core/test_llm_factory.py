"""Regression tests for `core/llm_factory` (NUMA-142 P6).

Circuit-breaker scoping. Each test names the defect it guards against, so a change
that reintroduces it fails here with the reason rather than a bare
assertion.
"""

import pytest


@pytest.mark.parametrize(
    "text, capacity",
    [
        ("429 too many requests", True),
        ("rate_limit_exceeded", True),
        ("503 service unavailable", True),
        ("request timed out", True),
        # A request-shaped fault must not open the breaker for every user.
        ("model_not_found: gpt-9", False),
        ("context_length_exceeded", False),
        ("invalid api key", False),
        # A permanent billing state: retry elsewhere, but do not zero the bucket.
        ("insufficient_quota", False),
    ],
)
def test_only_capacity_errors_open_the_circuit_breaker(text, capacity):
    from src.core.llm_factory import _is_capacity_error

    assert _is_capacity_error(text) is capacity
