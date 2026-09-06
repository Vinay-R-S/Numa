"""Regression tests for `core/oauth_state` (NUMA-142 P6).

Signed OAuth state. Each test names the defect it guards against, so a change
that reintroduces it fails here with the reason rather than a bare
assertion.
"""

import pytest


def test_oauth_state_round_trip():
    from src.core.oauth_state import issue_state, verify_state

    user_id = "11111111-2222-3333-4444-555555555555"
    assert verify_state(issue_state(user_id)) == user_id


@pytest.mark.parametrize(
    "state",
    [
        "",
        # A bare user id is the old Slack format: accepting it is the hole.
        "11111111-2222-3333-4444-555555555555",
        "abc.def",
        "not-base64.$$$",
        # Non-ASCII raised TypeError out of compare_digest as a 500.
        "abc.\u00fc",
    ],
)
def test_oauth_state_rejects_unusable_values(state):
    from src.core.oauth_state import verify_state

    assert verify_state(state) is None


def test_oauth_state_expires():
    from src.core.oauth_state import issue_state, verify_state

    assert verify_state(issue_state("someone", ttl_seconds=-1)) is None


def test_oauth_state_rejects_a_forged_signature():
    from src.core.oauth_state import issue_state, verify_state

    payload, _, _signature = issue_state("someone").partition(".")
    assert verify_state(f"{payload}.AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA") is None
