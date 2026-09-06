"""Regression tests for `health_agent/agent` (NUMA-142 P6).

Diet-query routing. Each test names the defect it guards against, so a change
that reintroduces it fails here with the reason rather than a bare
assertion.
"""

import pytest


@pytest.mark.parametrize(
    "query",
    [
        # Every one of these matched the bare substring "eat" and returned a
        # canned meal plan without running a single tool.
        "my heart beats fast",
        "what breathing exercises help",
        "how much did I sweat today",
        "great job on my steps",
        "how many calories did I burn",
    ],
)
def test_non_diet_queries_do_not_hit_the_diet_planner(query):
    from src.health_agent.agent import _is_diet_query

    assert _is_diet_query(query) is False


@pytest.mark.parametrize(
    "query",
    [
        "what should I eat today",
        "plan my meals",
        "give me a diet plan",
        "how much protein do I need",
        "what is my calorie intake",
    ],
)
def test_diet_queries_still_route_to_the_diet_planner(query):
    from src.health_agent.agent import _is_diet_query

    assert _is_diet_query(query) is True
