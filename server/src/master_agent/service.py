import importlib
import operator
import os
from datetime import date, datetime, time, timedelta, timezone
from functools import lru_cache
from typing import Annotated, Dict, List, Optional, Sequence, Tuple, TypedDict

from ..calendar_agent.service import run_agent_chat
from ..memory import memory_service
from ..tasks import service as task_service
from ..slack_agent.service import run_slack_agent_chat
from ..health_agent.service import run_health_agent_chat
from ..github_agent.service import run_github_agent_chat
from ..leetcode.service import run_leetcode_agent_chat


MASTER_AGENT_SYSTEM_PROMPT = (
    "You are NUMA, a unified AI assistant that orchestrates specialized sub-agents "
    "to help users manage their digital life.\n\n"
    "DELEGATION TOOLS (pass the user's query to a specialized sub-agent):\n"
    "- delegate_to_calendar: For scheduling, viewing, modifying, or deleting calendar events\n"
    "- delegate_to_slack: For searching Slack messages, sending messages, Slack-sourced tasks\n"
    "- delegate_to_health: For health metrics, fitness data, diet plans, yoga suggestions\n"
    "- delegate_to_journal: For journal summaries, reflections, reading journal entries\n"
    "- auto_generate_journal: Auto-generate today's journal from all connected apps\n"
    "- delegate_to_github: For GitHub commits, pull requests, repositories, contribution stats\n"
    "- delegate_to_leetcode: For LeetCode stats, problem progress, rankings\n\n"
    "DIRECT TOOLS:\n"
    "- create_task / update_task / delete_task / list_tasks: Manage tasks directly\n"
    "- get_dashboard_overview: Get a summary of tasks, calendar, health stats\n\n"
    "RULES:\n"
    "1. Use delegation tools when the query belongs to a sub-agent domain.\n"
    "2. Use task tools directly for task operations.\n"
    "2a. For task card moves, always update the existing task status. Do not delete and recreate cards.\n"
    "2b. For a request to add one task, call create_task exactly once.\n"
    "3. For general or small-talk queries, respond directly without tools.\n"
    "4. When delegating, pass the user's full query for best results.\n"
    "5. Never fabricate data - always use tools to fetch real information.\n"
    "6. Do not use emojis.\n"
    "Keep responses concise and action-oriented. Use plain Markdown when structure helps."
)

TASK_SUBAGENT_SYSTEM_PROMPT = (
    "You are NUMA Task sub-agent. "
    "You can only operate through tools to create, update, delete, and list tasks. "
    "If required details are missing, ask a short clarification question. "
    "Never invent task IDs or claim updates you did not perform. "
    "For card moves, update status only. Do not delete and recreate the task. "
    "For a request to add one task, call create_task exactly once. "
    "Do not use emojis."
)


class TaskAgentState(TypedDict):
    messages: Annotated[Sequence[object], operator.add]
    user_query: str
    semantic_context: str
    mutated: bool


class MasterAgentState(TypedDict):
    query: str
    history: List[dict]
    user_id: str
    semantic_context: str
    route: str
    response: str
    success: bool
    delegated_to: Optional[str]
    refreshCalendar: bool
    refreshTasks: bool
    refreshSlack: bool
    refreshHealth: bool
    refreshGithub: bool
    refreshJournal: bool


class MasterToolState(TypedDict):
    messages: Annotated[Sequence[object], operator.add]
    user_query: str
    user_id: str
    semantic_context: str


def _require_master_dependencies() -> Dict[str, object]:
    try:
        messages_module = importlib.import_module("langchain_core.messages")
        tools_module = importlib.import_module("langchain_core.tools")
        graph_module = importlib.import_module("langgraph.graph")

        return {
            "AIMessage": getattr(messages_module, "AIMessage"),
            "HumanMessage": getattr(messages_module, "HumanMessage"),
            "SystemMessage": getattr(messages_module, "SystemMessage"),
            "ToolMessage": getattr(messages_module, "ToolMessage"),
            "tool": getattr(tools_module, "tool"),
            "StateGraph": getattr(graph_module, "StateGraph"),
            "END": getattr(graph_module, "END"),
        }
    except Exception as exc:
        raise RuntimeError(
            "Master agent dependencies are missing. Install langchain, langgraph, and langchain-core."
        ) from exc


def _get_llm(model_override: Optional[str] = None, user_id: Optional[str] = None):
    from ..llm_factory import get_llm_with_fallback
    return get_llm_with_fallback(
        user_id=user_id,
        agent_name="master",
        priority="high",
        model=model_override,
    )


def _is_llm_configured(user_id: Optional[str] = None) -> bool:
    from ..llm_factory import is_any_llm_configured
    return is_any_llm_configured(user_id)


def _history_to_messages(history: List[dict], HumanMessage, AIMessage) -> List[object]:
    messages: List[object] = []
    for message in history:
        content = (message.get("content") or "").strip()
        if not content:
            continue

        role = (message.get("role") or "").lower()
        if role == "user":
            messages.append(HumanMessage(content=content))
        elif role in ("assistant", "ai"):
            messages.append(AIMessage(content=content))

    return messages


def _parse_due_datetime(value: str | None):
    if not value:
        return None

    text = value.strip()
    if not text:
        return None

    if text.endswith("Z"):
        text = text[:-1] + "+00:00"

    try:
        dt = datetime.fromisoformat(text)
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        pass

    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            parsed = datetime.strptime(text, fmt)
            return parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            continue

    return None


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


def _format_local_time(value) -> str:
    if isinstance(value, datetime):
        return value.strftime("%H:%M")
    return str(value or "")


def _fetch_day_planning_context(user_id: str) -> Dict:
    from ..calendar import service as calendar_service
    from ..db import _get_conn

    now = datetime.now(calendar_service.TIMEZONE)
    today = now.date()
    day_start = datetime.combine(today, time.min).replace(tzinfo=calendar_service.TIMEZONE)
    day_end = day_start + timedelta(days=1)

    context: Dict = {
        "today": today,
        "now": now,
        "events": [],
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
              AND e.start_at >= %s
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

        cur.execute(
            """
            SELECT steps, active_minutes, calories, distance_km, sleep_hours
            FROM public.health_snapshots
            WHERE user_id = %s AND snapshot_date = %s
            """,
            (user_id, today),
        )
        health_rows = cur.fetchall()
        if health_rows:
            context["health"] = {
                "steps": max((row[0] or 0) for row in health_rows),
                "active_minutes": max((row[1] or 0) for row in health_rows),
                "calories": max((row[2] or 0) for row in health_rows),
                "distance_km": max((row[3] or 0) for row in health_rows),
                "sleep_hours": max((row[4] or 0) for row in health_rows),
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
        context["db_error"] = "Some planning context could not be loaded."
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

    for event in events:
        title = str(event.get("title") or "Meeting").strip()
        start = event.get("start_at")
        end = event.get("end_at")
        cal_id = str(event.get("google_cal_id") or "primary")
        event_id = str(event.get("google_event_id") or "").strip()
        if not title or not event_id or not isinstance(start, datetime):
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
            f"{steps:,} steps, {active} active min, {sleep or 0}h sleep"
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


def _task_toolset(tool_decorator, user_id: str):
    @tool_decorator
    def create_task(
        title: str,
        description: str = "",
        status: str = "planned",
        due_datetime: str = "",
    ) -> str:
        """Create a task with optional description, status, and due datetime."""
        try:
            normalized_status = status.strip().lower() or "planned"
            if normalized_status not in {"planned", "inprogress", "completed", "pending"}:
                return "Invalid status. Use planned, inprogress, completed, or pending."

            due = _parse_due_datetime(due_datetime)
            task = task_service.create_task_for_user(
                user_id=user_id,
                title=title.strip(),
                description=description.strip() or None,
                status=normalized_status,
                due_date=due,
                source_name="NUMA Agent",
            )
            return f"Task created: {task.get('title')} [{task.get('status')}]."
        except Exception as exc:
            return f"Error creating task: {exc}"

    @tool_decorator
    def update_task(
        title: str,
        new_title: str = "",
        description: str = "",
        status: str = "",
    ) -> str:
        """Update an existing task identified by title."""
        try:
            normalized_status = status.strip().lower() or None
            if normalized_status and normalized_status not in {"planned", "inprogress", "completed", "pending"}:
                return "Invalid status. Use planned, inprogress, completed, or pending."

            if not any((new_title.strip(), description.strip(), normalized_status)):
                return "Please provide at least one update field: new_title, description, or status."

            updated = task_service.update_task_by_title(
                user_id=user_id,
                title=title.strip(),
                new_title=new_title.strip() or None,
                description=description.strip() or None,
                status=normalized_status,
            )
            if not updated:
                return f"Task not found: {title}."

            return f"Task updated: {updated.get('title')} [{updated.get('status')}]."
        except Exception as exc:
            return f"Error updating task: {exc}"

    @tool_decorator
    def delete_task(title: str) -> str:
        """Delete a task by title."""
        try:
            deleted = task_service.delete_task_by_title(user_id=user_id, title=title.strip())
            if deleted == 0:
                return f"Task not found: {title}."
            return f"Task deleted: {title}."
        except Exception as exc:
            return f"Error deleting task: {exc}"

    @tool_decorator
    def list_tasks(limit: int = 10) -> str:
        """List recent tasks up to the given limit."""
        try:
            safe_limit = max(1, min(limit, 50))
            tasks = task_service.list_recent_tasks(user_id=user_id, limit=safe_limit)
            if not tasks:
                return "You have no tasks right now."

            lines = ["Recent tasks:"]
            for task in tasks:
                due = task.get("due_date")
                due_text = due.isoformat() if isinstance(due, datetime) else (str(due) if due else "none")
                lines.append(f"- {task.get('title', 'Untitled')} [{task.get('status', 'planned')}] due={due_text}")
            return "\n".join(lines)
        except Exception as exc:
            return f"Error listing tasks: {exc}"

    return [create_task, update_task, delete_task, list_tasks]


@lru_cache(maxsize=64)
def _build_task_subagent_graph(user_id: str, model_override: Optional[str] = None):
    deps = _require_master_dependencies()

    AIMessage = deps["AIMessage"]
    SystemMessage = deps["SystemMessage"]
    ToolMessage = deps["ToolMessage"]
    StateGraph = deps["StateGraph"]
    END = deps["END"]

    tools = _task_toolset(deps["tool"], user_id)
    tool_map = {tool.name: tool for tool in tools}

    required_args = {
        "create_task": {"title"},
        "update_task": {"title"},
        "delete_task": {"title"},
    }
    mutation_tools = {"create_task", "update_task", "delete_task"}

    def validate_tool_call(tool_name: str, args: dict) -> str | None:
        required = required_args.get(tool_name)
        if not required:
            return None
        missing = [key for key in required if key not in args]
        if missing:
            return f"Missing required arguments for {tool_name}: {missing}"
        return None

    def call_model(state: TaskAgentState) -> TaskAgentState:
        llm = _get_llm(model_override=model_override, user_id=user_id)
        llm_with_tools = llm.bind_tools(tools)

        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        semantic_context = (state.get("semantic_context") or "").strip()
        context_block = ""
        if semantic_context:
            context_block = (
                "\nRelevant semantic memory (user-scoped):\n"
                f"{semantic_context}\n"
                "Use this only if it helps make task operations accurate."
            )

        system_prompt = (
            f"{TASK_SUBAGENT_SYSTEM_PROMPT}\n"
            f"Current time: {now}"
            f"{context_block}"
        )

        full_messages = [SystemMessage(content=system_prompt)] + list(state["messages"])
        response = llm_with_tools.invoke(full_messages)

        return {
            "messages": [response],
            "user_query": state["user_query"],
            "semantic_context": state["semantic_context"],
            "mutated": state["mutated"],
        }

    def call_tools(state: TaskAgentState) -> TaskAgentState:
        last_message = state["messages"][-1]
        tool_messages = []
        mutated = state["mutated"]

        for tool_call in getattr(last_message, "tool_calls", []):
            tool_name = tool_call.get("name")
            tool_args = tool_call.get("args", {})
            tool_id = tool_call.get("id")

            validation_error = validate_tool_call(tool_name, tool_args)
            if validation_error:
                result = validation_error
            elif tool_name not in tool_map:
                result = f"Unknown tool '{tool_name}'."
            else:
                try:
                    result = tool_map[tool_name].invoke(tool_args)
                    if tool_name in mutation_tools and not str(result).lower().startswith("error"):
                        mutated = True
                except Exception as exc:
                    result = f"Error executing {tool_name}: {exc}"

            tool_messages.append(ToolMessage(content=str(result), tool_call_id=tool_id))

        return {
            "messages": tool_messages,
            "user_query": state["user_query"],
            "semantic_context": state["semantic_context"],
            "mutated": mutated,
        }

    def should_continue(state: TaskAgentState):
        last_message = state["messages"][-1]
        tool_call_rounds = sum(
            1
            for message in state["messages"]
            if hasattr(message, "tool_calls") and message.tool_calls
        )

        if tool_call_rounds >= 6:
            return "end"

        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "call_tools"

        return "end"

    workflow = StateGraph(TaskAgentState)
    workflow.add_node("call_model", call_model)
    workflow.add_node("call_tools", call_tools)

    workflow.set_entry_point("call_model")
    workflow.add_conditional_edges(
        "call_model",
        should_continue,
        {"call_tools": "call_tools", "end": END},
    )
    workflow.add_edge("call_tools", "call_model")

    return workflow.compile(), AIMessage


def _run_task_subagent(
    query: str,
    history: List[dict],
    user_id: str,
    semantic_context: str,
    model: Optional[str] = None,
) -> Tuple[str, bool]:
    try:
        deps = _require_master_dependencies()
        HumanMessage = deps["HumanMessage"]
        AIMessage = deps["AIMessage"]

        graph, AIMessageType = _build_task_subagent_graph(user_id, model)

        history_messages = _history_to_messages(history, HumanMessage, AIMessage)
        initial_state: TaskAgentState = {
            "messages": history_messages + [HumanMessage(content=query)],
            "user_query": query,
            "semantic_context": semantic_context,
            "mutated": False,
        }

        result = graph.invoke(initial_state)
        messages = result.get("messages", [])
        if not messages:
            raise RuntimeError("Task sub-agent did not produce any response")

        final_message = messages[-1]
        response_text = getattr(final_message, "content", str(final_message))
        if isinstance(final_message, AIMessageType) and isinstance(response_text, list):
            response_text = "\n".join(str(part) for part in response_text)

        mutated = bool(result.get("mutated", False))
        response_string = str(response_text)

        if user_id and response_string.strip():
            memory_service.store_turn(user_id, query, response_string)

        return response_string, mutated
    except Exception as exc:
        return f"Error running task sub-agent: {exc}", False


# ---------------------------------------------------------------------------
# Master agent delegation + direct tools
# ---------------------------------------------------------------------------

def _master_toolset(tool_decorator, user_id: str, model_override: Optional[str] = None):
    """Create delegation + task + dashboard tools for the master agent."""
    refresh = {
        "refreshCalendar": False,
        "refreshTasks": False,
        "refreshSlack": False,
        "refreshHealth": False,
        "refreshGithub": False,
        "refreshJournal": False,
        "delegated_to": [],
        "_task_mutation_done": False,
    }

    @tool_decorator
    def delegate_to_calendar(query: str) -> str:
        """Delegate a calendar-related query to the Calendar sub-agent.
        Use for: creating events, checking schedule, managing meetings, finding free slots,
        rescheduling, deleting events, or any Google Calendar operations."""
        try:
            result = run_agent_chat(
                query=query, history=[], user_id=user_id, model=model_override,
                preloaded_context=refresh.get("_preloaded_context"),
            )
            if result.get("refreshCalendar"):
                refresh["refreshCalendar"] = True
                refresh["refreshTasks"] = True
            refresh["delegated_to"].append("calendar-subagent")
            return result.get("response", "No response from Calendar agent")
        except Exception as exc:
            return f"Calendar agent error: {exc}"

    @tool_decorator
    def delegate_to_slack(query: str) -> str:
        """Delegate a Slack-related query to the Slack sub-agent.
        Use for: searching Slack messages, sending messages to channels,
        creating tasks from Slack content, listing Slack-sourced tasks."""
        try:
            result = run_slack_agent_chat(
                query=query, history=[], user_id=user_id, model=model_override,
                preloaded_context=refresh.get("_preloaded_context"),
            )
            if result.get("refresh_slack"):
                refresh["refreshSlack"] = True
                refresh["refreshTasks"] = True
            refresh["delegated_to"].append("slack-subagent")
            return result.get("response", "No response from Slack agent")
        except Exception as exc:
            return f"Slack agent error: {exc}"

    @tool_decorator
    def delegate_to_health(query: str) -> str:
        """Delegate a health query to the Health sub-agent.
        Use for: health metrics, step count, calories, sleep data, diet recommendations,
        yoga suggestions, syncing Google Fit or Strava data."""
        try:
            result = run_health_agent_chat(
                query=query, history=[], user_id=user_id, model=model_override,
                preloaded_context=refresh.get("_preloaded_context"),
            )
            if result.get("refresh_health"):
                refresh["refreshHealth"] = True
            refresh["delegated_to"].append("health-subagent")
            return result.get("response", "No response from Health agent")
        except Exception as exc:
            return f"Health agent error: {exc}"

    @tool_decorator
    def delegate_to_journal(query: str) -> str:
        """Delegate a journal-related query to the Journal sub-agent.
        Use for: reading journal entries, getting daily summaries, daily reflections,
        or any journal content questions. For auto-generation use auto_generate_journal."""
        try:
            from ..journal.service import generate_daily_summary
            from datetime import date as _date

            q_lower = query.lower()
            if any(w in q_lower for w in ("summarize", "summary", "wrap up", "recap")):
                response_text = generate_daily_summary(user_id, _date.today())
            else:
                llm = _get_llm(model_override=model_override, user_id=user_id)
                response_text = _answer_general(
                    f"The user wants to interact with their journal. Help them: {query}",
                    "",
                    llm,
                )
            refresh["refreshJournal"] = True
            refresh["delegated_to"].append("journal-subagent")
            return response_text
        except Exception as exc:
            return f"Journal agent error: {exc}"

    @tool_decorator
    def auto_generate_journal() -> str:
        """Auto-generate today's journal entry from all connected apps data
        (calendar, tasks, health, Slack, GitHub). Use when the user asks to
        create or auto-generate a journal entry for today."""
        try:
            from ..journal.service import auto_generate_journal_entry

            result = auto_generate_journal_entry(user_id)
            refresh["refreshJournal"] = True
            refresh["delegated_to"].append("journal-subagent")
            title = result.get("title", "Untitled")
            mood = result.get("mood", "okay")
            return f"Journal generated: '{title}' (mood: {mood})"
        except Exception as exc:
            return f"Journal generation error: {exc}"

    @tool_decorator
    def delegate_to_github(query: str) -> str:
        """Delegate a GitHub-related query to the GitHub sub-agent.
        Use for: GitHub commits, pull requests, repositories, coding contribution stats,
        or any GitHub activity questions."""
        try:
            result = run_github_agent_chat(
                query=query, history=[], user_id=user_id, model=model_override,
                preloaded_context=refresh.get("_preloaded_context"),
            )
            if result.get("refresh_github"):
                refresh["refreshGithub"] = True
            refresh["delegated_to"].append("github-subagent")
            return result.get("response", "No response from GitHub agent")
        except Exception as exc:
            return f"GitHub agent error: {exc}"

    @tool_decorator
    def delegate_to_leetcode(query: str) -> str:
        """Delegate a LeetCode-related query to the LeetCode sub-agent.
        Use for: LeetCode stats, problem progress, rankings, submissions,
        or competitive programming questions."""
        try:
            result = run_leetcode_agent_chat(
                query=query, history=[], user_id=user_id, model=model_override,
                preloaded_context=refresh.get("_preloaded_context"),
            )
            refresh["delegated_to"].append("leetcode-subagent")
            return result.get("response", "No response from LeetCode agent")
        except Exception as exc:
            return f"LeetCode agent error: {exc}"

    @tool_decorator
    def get_dashboard_overview() -> str:
        """Get a dashboard overview of all stats: tasks, calendar events, health metrics.
        Use when the user asks for a general overview, status summary, or how their day looks."""
        try:
            from ..db import _get_conn
            from datetime import date as _date

            conn = _get_conn()
            lines = ["Dashboard Overview:"]
            try:
                cur = conn.cursor()

                cur.execute(
                    "SELECT status, COUNT(*) FROM public.tasks "
                    "WHERE user_id = %s GROUP BY status",
                    (user_id,),
                )
                task_rows = cur.fetchall()
                if task_rows:
                    total = sum(c for _, c in task_rows)
                    summary = ", ".join(f"{s}: {c}" for s, c in task_rows)
                    lines.append(f"Tasks ({total}): {summary}")
                else:
                    lines.append("Tasks: none")

                today = _date.today()
                start_of_day = datetime.combine(
                    today, datetime.min.time()
                ).replace(tzinfo=timezone.utc)
                end_of_day = start_of_day + timedelta(days=1)
                cur.execute(
                    "SELECT COUNT(*) FROM public.cal_events "
                    "WHERE user_id = %s AND start_at >= %s AND start_at < %s "
                    "AND deleted_at IS NULL",
                    (user_id, start_of_day, end_of_day),
                )
                event_count = cur.fetchone()[0]
                lines.append(f"Today's Calendar Events: {event_count}")

                cur.execute(
                    "SELECT steps, calories, active_minutes, sleep_hours "
                    "FROM public.health_snapshots "
                    "WHERE user_id = %s AND snapshot_date = %s LIMIT 1",
                    (user_id, today),
                )
                health_row = cur.fetchone()
                if health_row:
                    steps, cal, active, sleep = health_row
                    lines.append(
                        f"Health: {steps or 0:,} steps, {cal or 0:,} kcal, "
                        f"{active or 0} min active, {sleep or 0}h sleep"
                    )
                else:
                    lines.append("Health: no data for today")

                cur.close()
            finally:
                conn.close()

            return "\n".join(lines)
        except Exception as exc:
            return f"Dashboard error: {exc}"

    task_tools = _task_toolset(tool_decorator, user_id)

    delegation_tools = [
        delegate_to_calendar,
        delegate_to_slack,
        delegate_to_health,
        delegate_to_journal,
        auto_generate_journal,
        delegate_to_github,
        delegate_to_leetcode,
        get_dashboard_overview,
    ]

    return delegation_tools + task_tools, refresh


def _answer_general(query: str, semantic_context: str, llm) -> str:
    context_block = ""
    if semantic_context:
        context_block = (
            "\nRelevant semantic memory:\n"
            f"{semantic_context}\n"
            "Use this only if relevant."
        )

    prompt = (
        "You are NUMA master agent. Keep responses concise and action-oriented. "
        "Do not use emojis. Use plain Markdown when structure helps. "
        "Mention that you can operate Calendar, Task, Slack, Health, GitHub, LeetCode, and Journal sub-agents. "
        f"{context_block}\n\nUser: {query}"
    )
    response = llm.invoke(prompt)
    content = getattr(response, "content", "")
    if isinstance(content, list):
        content = "\n".join(str(part) for part in content)
    return str(content).strip() or "How can I help with your calendar or tasks?"


# ---------------------------------------------------------------------------
# Master agent tool-calling graph
# ---------------------------------------------------------------------------

@lru_cache(maxsize=64)
def _build_master_graph(user_id: str, model_override: Optional[str] = None):
    deps = _require_master_dependencies()

    AIMessage = deps["AIMessage"]
    SystemMessage = deps["SystemMessage"]
    ToolMessage = deps["ToolMessage"]
    StateGraph = deps["StateGraph"]
    END = deps["END"]

    tools, refresh_tracker = _master_toolset(deps["tool"], user_id, model_override)
    tool_map = {t.name: t for t in tools}
    task_mutation_tools = {"create_task", "update_task", "delete_task"}

    def call_model(state: MasterToolState) -> MasterToolState:
        llm = _get_llm(model_override=model_override, user_id=user_id)
        llm_with_tools = llm.bind_tools(tools)

        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        sem = (state.get("semantic_context") or "").strip()
        context = (
            f"\nRelevant semantic memory:\n{sem}\nUse only if relevant."
            if sem else ""
        )

        system = f"{MASTER_AGENT_SYSTEM_PROMPT}\nCurrent time: {now}{context}"
        full_messages = [SystemMessage(content=system)] + list(state["messages"])
        response = llm_with_tools.invoke(full_messages)

        return {
            "messages": [response],
            "user_query": state["user_query"],
            "user_id": state["user_id"],
            "semantic_context": state["semantic_context"],
        }

    def call_tools(state: MasterToolState) -> MasterToolState:
        last = state["messages"][-1]
        out = []
        for tc in getattr(last, "tool_calls", []):
            name = tc.get("name")
            args = tc.get("args", {})
            tid = tc.get("id")
            if name not in tool_map:
                result = f"Unknown tool '{name}'."
            else:
                try:
                    if name in task_mutation_tools and refresh_tracker.get("_task_mutation_done"):
                        result = (
                            "A task mutation has already been completed for this request. "
                            "Do not run another create, update, or delete."
                        )
                    else:
                        result = tool_map[name].invoke(args)
                    result_text = str(result).lower()
                    mutation_succeeded = result_text.startswith(
                        ("task created:", "task updated:", "task deleted:")
                    )
                    if name in task_mutation_tools and mutation_succeeded:
                        refresh_tracker["refreshTasks"] = True
                        refresh_tracker["_task_mutation_done"] = True
                except Exception as exc:
                    result = f"Error running {name}: {exc}"
            out.append(ToolMessage(content=str(result), tool_call_id=tid))
        return {
            "messages": out,
            "user_query": state["user_query"],
            "user_id": state["user_id"],
            "semantic_context": state["semantic_context"],
        }

    def should_continue(state: MasterToolState):
        last = state["messages"][-1]
        rounds = sum(
            1 for m in state["messages"]
            if hasattr(m, "tool_calls") and m.tool_calls
        )
        if rounds >= 8:
            return "end"
        if hasattr(last, "tool_calls") and last.tool_calls:
            return "call_tools"
        return "end"

    wf = StateGraph(MasterToolState)
    wf.add_node("call_model", call_model)
    wf.add_node("call_tools", call_tools)
    wf.set_entry_point("call_model")
    wf.add_conditional_edges(
        "call_model", should_continue,
        {"call_tools": "call_tools", "end": END},
    )
    wf.add_edge("call_tools", "call_model")

    return wf.compile(), AIMessage, refresh_tracker


def run_master_agent_chat(
    query: str,
    history: List[dict],
    user_id: Optional[str],
    model: Optional[str] = None,
) -> Dict:
    _empty = {
        "refreshCalendar": False, "refreshTasks": False, "refreshSlack": False,
        "refreshHealth": False, "refreshGithub": False, "refreshJournal": False,
    }

    if not user_id:
        return {"response": "Please sign in again. Your user session is missing.",
                "success": False, "delegated_to": None, **_empty}

    if _is_plan_my_day_query(query):
        try:
            return _run_day_planner(user_id, query)
        except Exception as exc:
            return {
                "response": f"Could not plan your day: {exc}",
                "success": False,
                "delegated_to": "master-day-planner",
                **_empty,
            }

    if not _is_llm_configured(user_id):
        return {
            "response": (
                "Master agent is unavailable - no LLM provider is configured. "
                "Go to Settings and add an API key for Groq, OpenAI, Anthropic, or Gemini, "
                "or configure an Ollama instance."
            ),
            "success": True, "delegated_to": None, **_empty,
        }

    try:
        # ── Smart data retrieval: plan → assemble context ────────────────
        try:
            from ..data_planner import plan_retrieval
            from ..context_assembler import assemble_context

            plan = plan_retrieval(user_id, query)
            assembled = assemble_context(user_id, plan)
            semantic_context = assembled.text
            import logging as _log
            _log.getLogger(__name__).info(
                "Smart retrieval: scope=%s, domains=%s, sources=%s, tokens≈%d, %.0fms",
                plan.temporal_scope, plan.domains, assembled.sources,
                assembled.token_estimate, assembled.retrieval_ms,
            )
        except Exception:
            # Fallback to legacy retrieval if smart planner fails
            semantic_context = memory_service.build_context_for_query(user_id, query)

        graph, AIMsg, refresh_tracker = _build_master_graph(user_id, model)

        for k in _empty:
            refresh_tracker[k] = False
        refresh_tracker["delegated_to"] = []
        refresh_tracker["_task_mutation_done"] = False
        # Store pre-loaded context so delegation tools can pass it to sub-agents
        refresh_tracker["_preloaded_context"] = semantic_context

        deps = _require_master_dependencies()
        HumanMessage = deps["HumanMessage"]
        AIMessage_cls = deps["AIMessage"]

        history_messages = _history_to_messages(history, HumanMessage, AIMessage_cls)

        initial_state: MasterToolState = {
            "messages": history_messages + [HumanMessage(content=query)],
            "user_query": query,
            "user_id": user_id,
            "semantic_context": semantic_context,
        }

        result = graph.invoke(initial_state)

        messages = result.get("messages", [])
        response_text = "How can I help you?"
        if messages:
            final = messages[-1]
            content = getattr(final, "content", str(final))
            if isinstance(content, list):
                content = "\n".join(str(part) for part in content)
            response_text = str(content).strip() or response_text

        if user_id and response_text.strip():
            memory_service.store_turn(user_id, query, response_text)

        delegated = refresh_tracker.get("delegated_to", [])
        delegated_to = ", ".join(delegated) if delegated else "master"

        return {
            "response": response_text,
            "success": True,
            "delegated_to": delegated_to,
            **{k: bool(refresh_tracker.get(k, False)) for k in _empty},
        }
    except Exception as exc:
        return {"response": f"Error running master agent: {exc}",
                "success": False, "delegated_to": None, **_empty}
