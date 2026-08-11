"""Slack Web API helpers: user-name resolution, channel lookup and message post
(NUMA-105 P3 / NUMA-115 P4, PLAN 16.2).

Holds the in-process workspace user-name cache. Extracted verbatim from
slack_agent/router.py; router.py re-exports these names.
"""
from __future__ import annotations

import json
import logging
import time
from typing import Optional

import httpx

from .config import _bot_token
from .persistence import _team_bot_token

log = logging.getLogger(__name__)

_slack_user_name_cache: dict[str, tuple[float, str]] = {}


def _raw_payload_dict(raw_payload) -> dict:
    if isinstance(raw_payload, dict):
        return raw_payload
    if isinstance(raw_payload, str):
        try:
            parsed = json.loads(raw_payload)
            return parsed if isinstance(parsed, dict) else {}
        except Exception:
            return {}
    return {}


def _name_from_slack_profile(payload: dict) -> Optional[str]:
    profile = payload.get("user_profile")
    if not isinstance(profile, dict):
        profile = {}

    for value in (
        profile.get("real_name"),
        profile.get("display_name"),
        profile.get("name"),
        payload.get("username"),
    ):
        if isinstance(value, str) and value.strip():
            return value.strip()

    return None


def _resolve_slack_user_name(team_id: str, slack_user_id: str, raw_payload=None) -> Optional[str]:
    payload_name = _name_from_slack_profile(_raw_payload_dict(raw_payload))
    if payload_name:
        return payload_name

    if not team_id or not slack_user_id:
        return None

    cache_key = f"{team_id}:{slack_user_id}"
    cached = _slack_user_name_cache.get(cache_key)
    if cached and time.time() - cached[0] < 3600:
        return cached[1]

    token = _team_bot_token(team_id) or _bot_token()
    if not token:
        return None

    try:
        with httpx.Client(timeout=8.0) as client:
            resp = client.get(
                "https://slack.com/api/users.info",
                headers={"Authorization": f"Bearer {token}"},
                params={"user": slack_user_id},
            )
        data = resp.json()
        if not data.get("ok"):
            return None
        user = data.get("user") if isinstance(data.get("user"), dict) else {}
        profile = user.get("profile") if isinstance(user.get("profile"), dict) else {}
        for value in (
            profile.get("real_name"),
            profile.get("display_name"),
            user.get("real_name"),
            user.get("name"),
        ):
            if isinstance(value, str) and value.strip():
                name = value.strip()
                _slack_user_name_cache[cache_key] = (time.time(), name)
                return name
    except Exception as exc:
        log.info("Slack user name lookup skipped for %s: %s", slack_user_id, exc)

    return None


def _cache_workspace_user_names(client: httpx.Client, token: str, team_id: str) -> None:
    if not token or not team_id:
        return

    cursor = ""
    while True:
        resp = client.get(
            "https://slack.com/api/users.list",
            headers={"Authorization": f"Bearer {token}"},
            params={"limit": "500", **({"cursor": cursor} if cursor else {})},
        )
        data = resp.json()
        if not data.get("ok"):
            log.info("Slack users.list skipped: %s", data.get("error"))
            return

        for member in data.get("members", []):
            if not isinstance(member, dict) or member.get("deleted"):
                continue
            slack_user_id = str(member.get("id") or "").strip()
            if not slack_user_id:
                continue
            profile = member.get("profile") if isinstance(member.get("profile"), dict) else {}
            for value in (
                profile.get("real_name"),
                profile.get("display_name"),
                member.get("real_name"),
                member.get("name"),
            ):
                if isinstance(value, str) and value.strip():
                    _slack_user_name_cache[f"{team_id}:{slack_user_id}"] = (time.time(), value.strip())
                    break

        cursor = (data.get("response_metadata") or {}).get("next_cursor") or ""
        if not cursor:
            return


def post_chat_message(
    token: str,
    channel_id: str,
    text: str,
    thread_ts: Optional[str] = None,
) -> dict:
    """POST chat.postMessage and return the raw Slack response body."""
    with httpx.Client(timeout=10.0) as client:
        resp = client.post(
            "https://slack.com/api/chat.postMessage",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "channel": channel_id,
                "text": text,
                **({"thread_ts": thread_ts} if thread_ts else {}),
            },
        )
    return resp.json()


def _resolve_channel_name(channel_id: str, team_id: Optional[str] = None) -> Optional[str]:
    bot = _team_bot_token(team_id or "") or _bot_token()
    if not bot:
        return None
    try:
        from slack_sdk import WebClient  # type: ignore
        wc   = WebClient(token=bot)
        info = wc.conversations_info(channel=channel_id)
        return info["channel"].get("name")
    except Exception:
        return None
