"""Plan-my-day pipeline: context fetch, free-slot allocation, plan synthesis
(NUMA-106 P3, PLAN 16.3).

Extracted verbatim from master_agent/service.py; service.py re-exports these
names so existing import paths keep working.
"""
import logging
from datetime import date, datetime, time, timedelta, timezone
from typing import Dict, List, Tuple

from ..memory import memory_service
from ..tasks import service as task_service
from .common import _format_local_time

log = logging.getLogger(__name__)


def _is_plan_my_day_query(query: str) -> bool:
    q = (query or "").strip().lower()
    triggers = (
        "plan my day",
        "plan out my day",
        "plan the day",
        "schedule my day",
        "organize my day",
        "make my day plan",
        "create my day plan",
        "day plan",
    )
    return any(trigger in q for trigger in triggers)


def _fetch_day_planning_context(user_id: str) -> Dict:
    from ..calendar import service as calendar_service
    from ..db import _get_conn
    from ..health_agent.repository import health_repository

    now = datetime.now(calendar_service.TIMEZONE)
    today = now.date()
    day_start = datetime.combine(today, time.min).replace(tzinfo=calendar_service.TIMEZONE)
    day_end = day_start + timedelta(days=1)

    context: Dict = {
        "today": today,
        "now": now,
        "events": [],
        # Specifically whether the calendar read succeeded. One `except` covers
        # all five queries, so keying the calendar-write guard on `db_error`
        # meant a failure in the last one (github_commits) suppressed
        # scheduling even though the events had loaded fine.
        "events_ok": False,
        "tasks": [],
        "health": {},
        "slack": [],
        "github": [],
    }

    conn = _get_conn()
    try:
        cur = conn.cursor()

        cur.execute(
            """
            SELECT e.google_event_id, e.title, e.description, e.start_at, e.end_at,
                   c.google_cal_id, c.name
            FROM public.cal_events e
            JOIN public.cal_calendars c ON c.id = e.calendar_id
            WHERE e.user_id = %s
              -- Overlap, not "starts today": an on-call block, a conference
              -- entry or an all-day event that began yesterday still occupies
              -- this morning, and filtering on start_at alone hid it from the
              -- free/busy picture the planner writes against (NUMA-142 P6).
              AND e.end_at > %s
              AND e.start_at < %s
              AND e.deleted_at IS NULL
              AND c.calendar_type IN ('personal', 'shared')
            ORDER BY e.start_at
            """,
            (user_id, day_start, day_end),
        )
        context["events"] = [
            {
                "google_event_id": row[0],
                "title": row[1],
                "description": row[2],
                "start_at": row[3],
                "end_at": row[4],
                "google_cal_id": row[5],
                "calendar_name": row[6],
            }
            for row in cur.fetchall()
        ]

        context["events_ok"] = True

        cur.execute(
            """
            SELECT title, description, status, priority, due_date, source_name
            FROM public.tasks
            WHERE user_id = %s
              AND status != 'completed'
              AND (
                due_date IS NULL
                OR (due_date >= %s AND due_date < %s)
              )
            ORDER BY
              CASE WHEN due_date IS NULL THEN 1 ELSE 0 END,
              due_date ASC,
              updated_at DESC
            LIMIT 12
            """,
            (user_id, day_start, day_end),
        )
        context["tasks"] = [
            {
                "title": row[0],
                "description": row[1],
                "status": row[2],
                "priority": row[3],
                "due_date": row[4],
                "source_name": row[5],
            }
            for row in cur.fetchall()
        ]

        # Through HealthRepository, on the connection this function already
        # holds (NUMA-143 P7, PLAN 10).
        health_rows = health_repository.day_metrics(user_id, today, conn=conn)
        if health_rows:
            def peak(metric: str):
                return max((row.get(metric) or 0) for row in health_rows)

            context["health"] = {
                "steps": peak("steps"),
                "active_minutes": peak("active_minutes"),
                "calories": peak("calories"),
                "distance_km": peak("distance_km"),
                "sleep_hours": peak("sleep_hours"),
                "heart_rate_bpm": peak("heart_rate_bpm"),
                # Summed, not peaked: heart points accumulate across sources.
                "heart_points": sum((row.get("heart_points") or 0) for row in health_rows),
            }

        cur.execute(
            """
            SELECT channel_name, text, created_at
            FROM public.slack_messages
            WHERE user_id = %s
              AND created_at >= %s
              AND created_at < %s
              AND COALESCE(text, '') <> ''
            ORDER BY created_at DESC
            LIMIT 8
            """,
            (user_id, day_start, day_end),
        )
        context["slack"] = [
            {"channel": row[0], "text": row[1], "created_at": row[2]}
            for row in cur.fetchall()
        ]

        cur.execute(
            """
            SELECT repo_full_name, message, committed_at
            FROM public.github_commits
            WHERE user_id = %s
              AND committed_at >= %s
              AND committed_at < %s
            ORDER BY committed_at DESC
            LIMIT 8
            """,
            (user_id, day_start, day_end),
        )
        context["github"] = [
            {"repo": row[0], "message": row[1], "committed_at": row[2]}
            for row in cur.fetchall()
        ]

        cur.close()
    except Exception:
        # Read by _run_day_planner before it writes anything to the calendar.
        # It used to be set and never looked at, so a failed events query
        # produced an empty list, the planner read that as a free day, and it
        # wrote NUMA Plan blocks over real meetings (NUMA-142 P6, PLAN 7).
        context["db_error"] = "Some planning context could not be loaded."
        log.warning("Day-planner context load failed for user %s", user_id, exc_info=True)
    finally:
        conn.close()

    return context


def _free_slots_for_day(events: List[Dict], now: datetime) -> List[Tuple[datetime, datetime]]:
    from ..calendar import service as calendar_service

    day = now.date()
    work_start = datetime.combine(day, time(9, 0)).replace(tzinfo=calendar_service.TIMEZONE)
    work_end = datetime.combine(day, time(18, 0)).replace(tzinfo=calendar_service.TIMEZONE)
    cursor = max(work_start, now.replace(second=0, microsecond=0) + timedelta(minutes=15))
    minute = (cursor.minute // 15 + (1 if cursor.minute % 15 else 0)) * 15
    cursor = cursor.replace(minute=0) + timedelta(minutes=minute)

    busy: List[Tuple[datetime, datetime]] = []
    for event in events:
        start = event.get("start_at")
        end = event.get("end_at")
        if isinstance(start, datetime) and isinstance(end, datetime):
            if start.tzinfo is None:
                start = start.replace(tzinfo=timezone.utc)
            if end.tzinfo is None:
                end = end.replace(tzinfo=timezone.utc)
            busy.append((start.astimezone(calendar_service.TIMEZONE), end.astimezone(calendar_service.TIMEZONE)))

    busy.sort(key=lambda pair: pair[0])
    slots: List[Tuple[datetime, datetime]] = []
    for start, end in busy:
        if end <= cursor:
            continue
        if start > cursor and (start - cursor) >= timedelta(minutes=30):
            slots.append((cursor, start))
        cursor = max(cursor, end)
    if cursor < work_end and (work_end - cursor) >= timedelta(minutes=30):
        slots.append((cursor, work_end))
    return slots


def _allocate_blocks(slots: List[Tuple[datetime, datetime]], durations: List[int]) -> List[Tuple[datetime, datetime]]:
    allocated: List[Tuple[datetime, datetime]] = []
    slot_index = 0
    for duration in durations:
        needed = timedelta(minutes=duration)
        while slot_index < len(slots):
            start, end = slots[slot_index]
            if end - start >= needed:
                block_end = start + needed
                allocated.append((start, block_end))
                slots[slot_index] = (block_end + timedelta(minutes=15), end)
                break
            slot_index += 1
    return allocated


def _run_day_planner(user_id: str, query: str) -> Dict:
    from ..calendar import service as calendar_service

    context = _fetch_day_planning_context(user_id)
    today: date = context["today"]
    now: datetime = context["now"]
    events: List[Dict] = context.get("events", [])
    tasks: List[Dict] = context.get("tasks", [])
    health: Dict = context.get("health", {})
    slack: List[Dict] = context.get("slack", [])
    github: List[Dict] = context.get("github", [])

    created_tasks: List[str] = []
    calendar_results: List[str] = []
    warnings: List[str] = []

    day_start = datetime.combine(today, time.min).replace(tzinfo=now.tzinfo)

    for event in events:
        title = str(event.get("title") or "Meeting").strip()
        start = event.get("start_at")
        end = event.get("end_at")
        cal_id = str(event.get("google_cal_id") or "primary")
        event_id = str(event.get("google_event_id") or "").strip()
        if not title or not event_id or not isinstance(start, datetime):
            continue
        # The events query is an overlap test, so it now also returns the
        # on-call block or conference entry that began yesterday. Those belong
        # in the free/busy picture but not as a task card due and reminding in
        # the past (NUMA-142 P6 review).
        if start < day_start:
            continue
        external_ref = task_service.calendar_external_ref(cal_id, event_id)
        desc = f"Calendar event from {event.get('calendar_name') or 'Google Calendar'}."
        if isinstance(end, datetime):
            desc += f" Time: {_format_local_time(start)}-{_format_local_time(end)}."
        try:
            task_service.upsert_calendar_event_task(
                user_id=user_id,
                external_ref=external_ref,
                title=title,
                description=desc,
                due_date=start,
                reminder_at=start - timedelta(minutes=15),
            )
            created_tasks.append(f"Meeting card: {title}")
        except Exception as exc:
            warnings.append(f"Could not create task card for calendar event '{title}': {exc}")

    plan_items: List[Dict] = []
    open_task_titles = [str(task.get("title") or "").strip() for task in tasks if str(task.get("title") or "").strip()]
    for title in open_task_titles[:4]:
        plan_items.append(
            {
                "title": f"Focus: {title}",
                "description": "Planned from your existing task list by NUMA day planner.",
                "duration": 60,
                "source": "Tasks",
            }
        )

    if slack:
        plan_items.append(
            {
                "title": "Review Slack follow-ups",
                "description": f"Review {len(slack)} recent Slack messages and convert important follow-ups into tasks.",
                "duration": 30,
                "source": "Slack",
            }
        )

    if github:
        repos = sorted({str(item.get("repo") or "").strip() for item in github if item.get("repo")})
        repo_text = ", ".join(repos[:3]) if repos else "recent repositories"
        plan_items.append(
            {
                "title": "GitHub review and code follow-up",
                "description": f"Review today's GitHub activity for {repo_text} and handle commits, PRs, or cleanup.",
                "duration": 60,
                "source": "GitHub",
            }
        )

    steps = health.get("steps") or 0
    active = health.get("active_minutes") or 0
    sleep = health.get("sleep_hours") or 0
    heart_rate = health.get("heart_rate_bpm") or 0
    heart_points = health.get("heart_points") or 0
    if health and (steps < 7000 or active < 45):
        plan_items.append(
            {
                "title": "Health break: walk and reset",
                "description": f"Based on today's health data: {steps:,} steps, {active} active minutes.",
                "duration": 30,
                "source": "Health",
            }
        )
    if health and sleep and sleep < 6:
        plan_items.append(
            {
                "title": "Keep evening light for recovery",
                "description": f"Sleep was {sleep:.1f} hours, so keep the evening lower intensity.",
                "duration": 30,
                "source": "Health",
            }
        )

    plan_items.append(
        {
            "title": "Daily wrap-up and tomorrow prep",
            "description": "Review completed work, update tasks, and prepare tomorrow's top priorities.",
            "duration": 30,
            "source": "NUMA",
        }
    )

    # An unreadable calendar is not an empty one. With no trustworthy free/busy
    # picture there are no free slots, so every plan item falls through to the
    # task-card branch below rather than being written into Google Calendar.
    if not context.get("events_ok"):
        warnings.append(
            "Your calendar could not be read, so nothing was scheduled on it. "
            "The plan was saved as task cards instead."
        )
        slots: List[Tuple[datetime, datetime]] = []
    else:
        slots = _free_slots_for_day(events, now)

    blocks = _allocate_blocks(slots, [int(item["duration"]) for item in plan_items])

    for index, item in enumerate(plan_items):
        start = blocks[index][0] if index < len(blocks) else None
        if start is None:
            due = datetime.combine(today, time(18, 0)).replace(tzinfo=calendar_service.TIMEZONE)
            external_ref = f"day-plan:{today.isoformat()}:{item['title'].lower().replace(' ', '-')[:64]}"
            try:
                task = task_service.create_task_for_user(
                    user_id=user_id,
                    title=item["title"],
                    description=item["description"],
                    status="planned",
                    due_date=due,
                    source_name=f"NUMA Day Plan - {item['source']}",
                    external_ref=external_ref,
                )
                created_tasks.append(str(task.get("title") or item["title"]))
            except Exception as exc:
                warnings.append(f"Could not create task '{item['title']}': {exc}")
            continue

        try:
            result = calendar_service.create_calendar_event(
                title=f"NUMA Plan: {item['title']}",
                datetime_str=start.strftime("%Y-%m-%d %H:%M"),
                duration_minutes=int(item["duration"]),
                attendees=None,
                create_meet=False,
                user_id=user_id,
            )
            if result.get("status") == "duplicate_prevented":
                calendar_results.append(f"Already on calendar: {item['title']} at {start.strftime('%H:%M')}")
            else:
                calendar_results.append(f"{item['title']} at {start.strftime('%H:%M')}")
            created_tasks.append(f"Calendar task: {item['title']}")
        except Exception as exc:
            warnings.append(f"Calendar block skipped for '{item['title']}': {exc}")
            due = start
            external_ref = f"day-plan:{today.isoformat()}:{item['title'].lower().replace(' ', '-')[:64]}"
            try:
                task = task_service.create_task_for_user(
                    user_id=user_id,
                    title=item["title"],
                    description=item["description"],
                    status="planned",
                    due_date=due,
                    source_name=f"NUMA Day Plan - {item['source']}",
                    external_ref=external_ref,
                )
                created_tasks.append(str(task.get("title") or item["title"]))
            except Exception as task_exc:
                warnings.append(f"Could not create fallback task '{item['title']}': {task_exc}")

    lines = [
        f"Planned your day for {today.isoformat()}.",
        "",
        "Data used:",
        f"- Calendar meetings: {len(events)}",
        f"- Open tasks considered: {len(tasks)}",
        f"- Slack messages considered: {len(slack)}",
        f"- GitHub items considered: {len(github)}",
        "- Health data: " + (
            f"{steps:,} steps, {active} active min, {sleep or 0}h sleep, "
            f"{heart_rate or 0} bpm, {heart_points or 0} heart points"
            if health else "not available"
        ),
        "",
        f"Task cards created or updated: {len(created_tasks)}",
    ]
    for title in created_tasks[:12]:
        lines.append(f"- {title}")

    lines.append("")
    if calendar_results:
        lines.append("Google Calendar blocks added:")
        for item in calendar_results:
            lines.append(f"- {item}")
    else:
        lines.append("Google Calendar blocks added: none")

    if warnings:
        lines.append("")
        lines.append("Notes:")
        for warning in warnings[:6]:
            lines.append(f"- {warning}")

    response = "\n".join(lines)
    if user_id and response.strip():
        memory_service.store_turn(user_id, query, response)

    return {
        "response": response,
        "success": True,
        "delegated_to": "master-day-planner",
        "refreshCalendar": bool(calendar_results),
        "refreshTasks": bool(created_tasks),
        "refreshSlack": False,
        "refreshHealth": False,
        "refreshGithub": False,
        "refreshJournal": False,
    }
