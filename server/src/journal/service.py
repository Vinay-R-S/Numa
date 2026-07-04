"""
Journal Service - AI-powered daily summary generation.

Collects data from journal entry, calendar events, tasks, health snapshots,
and Slack messages for the target date, then produces a cohesive summary
using the user's configured LLM provider.
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone

from .repository import journal_repository

log = logging.getLogger(__name__)

SUMMARY_SYSTEM_PROMPT = (
    "You are NUMA Journal assistant. Given the user's daily data (journal entry, "
    "calendar events, completed tasks, health metrics, Slack highlights), write a "
    "warm, concise summary of their day in 3-5 sentences. Focus on accomplishments, "
    "mood, and wellbeing. Do not fabricate data - only reference what is provided."
)


def _day_bounds(target_date: date):
    start = datetime.combine(target_date, datetime.min.time()).replace(tzinfo=timezone.utc)
    return start, start + timedelta(days=1)


def _fetch_journal_content(user_id: str, target_date: date) -> str:
    row = journal_repository.content_row(user_id, target_date)
    if not row:
        return ""
    title, content, mood, tags = row
    parts = []
    if title:
        parts.append(f"Journal title: {title}")
    if content:
        parts.append(f"Journal: {content[:1000]}")
    if mood:
        parts.append(f"Mood: {mood}")
    if tags:
        parts.append(f"Tags: {', '.join(tags)}")
    return "\n".join(parts)


def _fetch_calendar_events(user_id: str, target_date: date) -> str:
    try:
        start, end = _day_bounds(target_date)
        rows = journal_repository.calendar_events(user_id, start, end)
        if not rows:
            return ""
        lines = ["Calendar events:"]
        for title, s, e in rows:
            lines.append(f"  - {title} ({s.strftime('%H:%M')} - {e.strftime('%H:%M')})")
        return "\n".join(lines)
    except Exception:
        return ""


def _fetch_completed_tasks(user_id: str, target_date: date) -> str:
    try:
        start, end = _day_bounds(target_date)
        rows = journal_repository.completed_tasks(user_id, start, end)
        if not rows:
            return ""
        lines = [f"Completed tasks ({len(rows)}):"]
        for title, status in rows:
            lines.append(f"  - {title} [{status}]")
        return "\n".join(lines)
    except Exception:
        return ""


def _fetch_health_data(user_id: str, target_date: date) -> str:
    try:
        rows = journal_repository.health_rows(user_id, target_date)
        if not rows:
            return ""
        lines = ["Health data:"]
        for src, steps, active, cal, dist, sleep, heart_rate, heart_points in rows:
            parts = [f"Source: {src}"]
            if steps:
                parts.append(f"Steps: {steps:,}")
            if active:
                parts.append(f"Active: {active}min")
            if cal:
                parts.append(f"Calories: {cal:,}")
            if dist:
                parts.append(f"Distance: {dist}km")
            if sleep:
                parts.append(f"Sleep: {sleep}h")
            if heart_rate:
                parts.append(f"Heart rate: {heart_rate:g} bpm")
            if heart_points:
                parts.append(f"Heart points: {heart_points:g}")
            lines.append(f"  {', '.join(parts)}")
        return "\n".join(lines)
    except Exception:
        return ""


def _fetch_slack_highlights(user_id: str, target_date: date) -> str:
    try:
        start, end = _day_bounds(target_date)
        rows = journal_repository.slack_highlights(user_id, start, end)
        if not rows:
            return ""
        lines = [f"Slack highlights ({len(rows)} messages):"]
        for channel, sender, text in rows:
            snippet = (text or "")[:120]
            lines.append(f"  - #{channel} ({sender}): {snippet}")
        return "\n".join(lines)
    except Exception:
        return ""


def _fetch_github_activity(user_id: str, target_date: date | None = None) -> str:
    try:
        row = journal_repository.github_username(user_id)
        if not row or not row[0]:
            return ""
        username = row[0]
        if target_date is None:
            return f"GitHub: Connected as {username}"

        start, end = _day_bounds(target_date)
        commits = journal_repository.github_commits(user_id, start, end)
        if not commits:
            return f"GitHub: Connected as {username}"
        lines = [f"GitHub activity for {username} ({len(commits)} cached commits):"]
        for repo, message in commits:
            lines.append(f"  - {repo}: {(message or 'Commit')[:120]}")
        return "\n".join(lines)
    except Exception:
        return ""


AUTO_GENERATE_SYSTEM_PROMPT = (
    "You are NUMA Journal assistant. Based on the user's day data (calendar events, "
    "tasks, health metrics, Slack highlights, GitHub activity), generate a complete "
    "journal entry. You MUST respond with EXACTLY these four lines, no extra text:\n"
    "TITLE: <a meaningful, specific title for today's journal entry>\n"
    "MOOD: <one of: great, good, okay, bad, terrible>\n"
    "TAGS: <comma-separated relevant tags, 2-5 tags>\n"
    "CONTENT: <a detailed, warm journal entry covering activities, accomplishments, "
    "health, and communications from the day, 3-8 sentences>\n\n"
    "Do not fabricate data - only reference what is provided. If very little data "
    "is available, write a shorter but still meaningful entry."
)


def _parse_generated_entry(raw: str) -> dict:
    """Parse LLM output into structured fields."""
    result = {"title": "", "content": "", "mood": "okay", "tags": []}
    for line in raw.strip().splitlines():
        line = line.strip()
        upper = line.upper()
        if upper.startswith("TITLE:"):
            result["title"] = line[6:].strip()
        elif upper.startswith("MOOD:"):
            mood_val = line[5:].strip().lower()
            if mood_val in ("great", "good", "okay", "bad", "terrible"):
                result["mood"] = mood_val
        elif upper.startswith("TAGS:"):
            raw_tags = line[5:].strip()
            result["tags"] = [t.strip() for t in raw_tags.split(",") if t.strip()]
        elif upper.startswith("CONTENT:"):
            result["content"] = line[8:].strip()
    if not result["title"]:
        result["title"] = f"Journal - {date.today()}"
    if not result["content"]:
        result["content"] = raw.strip()
    return result


def auto_generate_journal_entry(user_id: str) -> dict:
    """Collect today's data from all connected apps and generate a journal entry via LLM."""
    target_date = date.today()

    sections = [
        _fetch_calendar_events(user_id, target_date),
        _fetch_completed_tasks(user_id, target_date),
        _fetch_health_data(user_id, target_date),
        _fetch_slack_highlights(user_id, target_date),
        _fetch_github_activity(user_id),
    ]

    data_block = "\n\n".join(s for s in sections if s)
    if not data_block.strip():
        return {
            "title": f"My Day - {target_date.strftime('%B %d, %Y')}",
            "content": "No activity data was found for today. Start using your connected apps and come back later!",
            "mood": "okay",
            "tags": ["auto-generated"],
            "entry_date": target_date,
        }

    from ..llm_factory import get_llm, is_any_llm_configured

    if not is_any_llm_configured(user_id):
        raise ValueError(
            "AI generation unavailable - no LLM provider configured. "
            "Go to Settings to add an API key."
        )

    llm = get_llm(user_id=user_id)
    prompt = (
        f"{AUTO_GENERATE_SYSTEM_PROMPT}\n\n"
        f"Date: {target_date}\n\n"
        f"--- User's Day Data ---\n{data_block}\n\n"
        "Generate the journal entry now:"
    )

    response = llm.invoke(prompt)
    raw_content = getattr(response, "content", str(response))
    if isinstance(raw_content, list):
        raw_content = "\n".join(str(p) for p in raw_content)

    parsed = _parse_generated_entry(str(raw_content))
    parsed["entry_date"] = target_date
    if "auto-generated" not in parsed["tags"]:
        parsed["tags"].append("auto-generated")
    return parsed


def generate_daily_summary(user_id: str, target_date: date) -> str:
    """Collect daily data and generate an AI summary."""
    sections = [
        _fetch_journal_content(user_id, target_date),
        _fetch_calendar_events(user_id, target_date),
        _fetch_completed_tasks(user_id, target_date),
        _fetch_health_data(user_id, target_date),
        _fetch_slack_highlights(user_id, target_date),
        _fetch_github_activity(user_id, target_date),
    ]

    data_block = "\n\n".join(s for s in sections if s)
    if not data_block.strip():
        return f"No data recorded for {target_date}. Start by writing in your journal!"

    try:
        from ..llm_factory import get_llm, is_any_llm_configured

        if not is_any_llm_configured(user_id):
            return (
                "AI summary unavailable - no LLM provider configured. "
                "Go to Settings to add an API key."
            )

        llm = get_llm(user_id=user_id)
        prompt = (
            f"{SUMMARY_SYSTEM_PROMPT}\n\n"
            f"Date: {target_date}\n\n"
            f"--- User's Day Data ---\n{data_block}\n\n"
            "Write a warm, concise daily summary:"
        )
        response = llm.invoke(prompt)
        content = getattr(response, "content", str(response))
        if isinstance(content, list):
            content = "\n".join(str(p) for p in content)
        return str(content).strip()
    except Exception as exc:
        log.error("Journal summary generation failed: %s", exc)
        return f"Could not generate summary: {exc}"
