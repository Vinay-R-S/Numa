"""Master-agent orchestration: delegation/task toolset, general answer, master
LangGraph build, and chat entrypoint (NUMA-106 P3, PLAN 16.3).

Extracted verbatim from master_agent/service.py; service.py re-exports these
names so existing import paths keep working.
"""
import contextvars
import logging
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from typing import Dict, List, Optional

from ..calendar_agent.service import run_agent_chat
from ..core.timezones import user_timezone, user_today
from ..github_agent.service import run_github_agent_chat
from ..health_agent.service import run_health_agent_chat
from ..leetcode.service import run_leetcode_agent_chat
from ..memory import memory_service
from ..slack_agent.service import run_slack_agent_chat
from .common import (
    _get_llm,
    _history_to_messages,
    _is_llm_configured,
    _require_master_dependencies,
)
from .day_planner import _is_plan_my_day_query, _run_day_planner
from .state import MasterToolState
from .subagents.task_agent import _task_toolset


log = logging.getLogger(__name__)

# Per request, not per compiled graph. `_build_master_graph` is lru_cached on
# (user_id, model_override), so two concurrent requests from one user shared one
# tracker dict: B's reset cleared A's flags mid-flight, re-armed the task
# mutation guard so A's model could create a second task, and overwrote the
# preloaded context A's delegation tools were about to hand to the sub-agents
# (NUMA-142 P6, PLAN 7). A ContextVar is per request and per thread, so the
# cached graph's closures still reach the right one.
_refresh_ctx: contextvars.ContextVar = contextvars.ContextVar("master_refresh_tracker")


def _new_refresh_state() -> dict:
    return {
        "refreshCalendar": False,
        "refreshTasks": False,
        "refreshSlack": False,
        "refreshHealth": False,
        "refreshGithub": False,
        "refreshJournal": False,
        "delegated_to": [],
        "_task_mutation_done": False,
    }


class _RefreshTracker:
    """Dict-like view of the current request's refresh flags."""

    @staticmethod
    def _current() -> dict:
        state = _refresh_ctx.get(None)
        if state is None:
            state = _new_refresh_state()
            _refresh_ctx.set(state)
        return state

    def __getitem__(self, key):
        return self._current()[key]

    def __setitem__(self, key, value):
        self._current()[key] = value

    def get(self, key, default=None):
        return self._current().get(key, default)

    @staticmethod
    def reset() -> None:
        _refresh_ctx.set(_new_refresh_state())


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


def _master_toolset(tool_decorator, user_id: str, model_override: Optional[str] = None):
    """Create delegation + task + dashboard tools for the master agent."""
    refresh = _RefreshTracker()

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
            log.warning("Calendar delegation failed: %s", exc, exc_info=True)
            return "The calendar assistant is unavailable right now."

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
            log.warning("Slack delegation failed: %s", exc, exc_info=True)
            return "The slack assistant is unavailable right now."

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
            if result.get("refresh_tasks"):
                refresh["refreshTasks"] = True
            refresh["delegated_to"].append("health-subagent")
            return result.get("response", "No response from Health agent")
        except Exception as exc:
            log.warning("Health delegation failed: %s", exc, exc_info=True)
            return "The health assistant is unavailable right now."

    @tool_decorator
    def delegate_to_journal(query: str) -> str:
        """Delegate a journal-related query to the Journal sub-agent.
        Use for: reading journal entries, getting daily summaries, daily reflections,
        or any journal content questions. For auto-generation use auto_generate_journal."""
        try:
            from ..journal.service import SummaryUnavailable, generate_daily_summary

            q_lower = query.lower()
            if any(w in q_lower for w in ("summarize", "summary", "wrap up", "recap")):
                try:
                    response_text = generate_daily_summary(user_id, user_today(user_id))
                except SummaryUnavailable as exc:
                    return str(exc)
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
            log.warning("Journal delegation failed: %s", exc, exc_info=True)
            return "The journal assistant is unavailable right now."

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
            log.warning("Journal auto-generation failed: %s", exc, exc_info=True)
            return "Could not generate the journal entry right now."

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
            if result.get("refresh_tasks"):
                refresh["refreshTasks"] = True
            refresh["delegated_to"].append("github-subagent")
            return result.get("response", "No response from GitHub agent")
        except Exception as exc:
            log.warning("GitHub delegation failed: %s", exc, exc_info=True)
            return "The github assistant is unavailable right now."

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
            if result.get("mutated"):
                refresh["refreshTasks"] = True
            refresh["delegated_to"].append("leetcode-subagent")
            return result.get("response", "No response from LeetCode agent")
        except Exception as exc:
            log.warning("LeetCode delegation failed: %s", exc, exc_info=True)
            return "The LeetCode assistant is unavailable right now."

    @tool_decorator
    def get_dashboard_overview() -> str:
        """Get a dashboard overview of all stats: tasks, calendar events, health metrics.
        Use when the user asks for a general overview, status summary, or how their day looks."""
        try:
            from ..db import _get_conn
            from ..health_agent.repository import health_repository

            # Resolved before the connection is taken. `user_timezone` reads
            # public.profiles through the same bounded pool, and holding one
            # slot while queueing for a second is how ten concurrent overviews
            # deadlock into PoolError (NUMA-142 P6 review).
            tz = user_timezone(user_id)
            today = datetime.now(tz).date()

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

                # The user's day, and its own zone's midnight. This paired a
                # server-local date with a UTC tzinfo, so it disagreed with the
                # day planner by the user's offset (NUMA-142 P6, PLAN 7).
                start_of_day = datetime.combine(today, datetime.min.time(), tzinfo=tz)
                end_of_day = start_of_day + timedelta(days=1)
                cur.execute(
                    "SELECT COUNT(*) FROM public.cal_events "
                    "WHERE user_id = %s AND start_at >= %s AND start_at < %s "
                    "AND deleted_at IS NULL",
                    (user_id, start_of_day, end_of_day),
                )
                event_count = cur.fetchone()[0]
                lines.append(f"Today's Calendar Events: {event_count}")

                # Through HealthRepository on this connection (NUMA-143 P7).
                # Every source for the day, not `LIMIT 1`: a user syncing both
                # Google Fit and Strava got whichever row Postgres returned
                # first, so half their day was invisible to the overview.
                health_rows = health_repository.day_metrics(user_id, today, conn=conn)
                if health_rows:
                    def peak(metric: str):
                        return max((row.get(metric) or 0) for row in health_rows)

                    heart_points = sum(
                        (row.get("heart_points") or 0) for row in health_rows
                    )
                    lines.append(
                        f"Health: {peak('steps'):,} steps, {peak('calories'):,} kcal, "
                        f"{peak('active_minutes')} min active, {peak('sleep_hours')}h sleep, "
                        f"{peak('heart_rate_bpm')} bpm, {heart_points} heart points"
                    )
                else:
                    lines.append("Health: no data for today")

                cur.close()
            finally:
                conn.close()

            return "\n".join(lines)
        except Exception as exc:
            log.warning("Dashboard overview failed: %s", exc, exc_info=True)
            return "Could not read the dashboard overview right now."

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
        # Smart data retrieval: plan then assemble context
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

        # One fresh state for this request, rather than resetting one shared
        # with every other in-flight request for the same user.
        refresh_tracker.reset()
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
        # Logged, not returned: the message is a response body and the raw text
        # carries provider hosts and driver detail (NUMA-142 P6, PLAN 8).
        log.error("Master agent error: %s", exc, exc_info=True)
        return {"response": "The assistant hit an error. Please try again.",
                "success": False, "delegated_to": None, **_empty}
