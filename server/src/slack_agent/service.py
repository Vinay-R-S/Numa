"""
Slack Sub-Agent Service
=======================
LangGraph agentic loop that handles Slack-related queries routed from
the Master Agent.

Tools available to the LLM
---------------------------
search_slack_messages   - semantic search over Qdrant
get_recent_messages     - PostgreSQL fetch (last N rows)
send_slack_message      - Slack Web API post
create_task_from_slack  - insert into public.tasks (source_name='Slack')
list_slack_tasks        - list tasks where source_name='Slack'

Entry point
-----------
run_slack_agent_chat(query, history, user_id, model=None) -> Dict
"""
from __future__ import annotations

import importlib
import json
import logging
import os
import re
from datetime import datetime, timezone
from typing import Annotated, Dict, List, Optional, Sequence, Tuple, TypedDict

import operator

log = logging.getLogger(__name__)

SLACK_AGENT_SYSTEM_PROMPT = (
    "You are NUMA Slack sub-agent. You help users interact with their Slack workspace. "
    "You can search recent Slack messages, send messages to channels, and create tasks from Slack content. "
    "Always use tools to fetch real data - never fabricate messages or channel names. "
    "If Slack credentials are not configured, inform the user politely and guide them to Settings → Connect Slack. "
    "Keep responses concise and action-oriented."
)


# ── LangGraph state ───────────────────────────────────────────────────────────

class SlackAgentState(TypedDict):
    messages: Annotated[Sequence[object], operator.add]
    user_query: str
    user_id: str
    semantic_context: str
    mutated: bool


# ── Dependency loader ─────────────────────────────────────────────────────────

def _require_deps() -> Dict:
    try:
        msgs_mod  = importlib.import_module("langchain_core.messages")
        tools_mod = importlib.import_module("langchain_core.tools")
        graph_mod = importlib.import_module("langgraph.graph")

        return {
            "AIMessage":    getattr(msgs_mod,  "AIMessage"),
            "HumanMessage": getattr(msgs_mod,  "HumanMessage"),
            "SystemMessage": getattr(msgs_mod, "SystemMessage"),
            "ToolMessage":  getattr(msgs_mod,  "ToolMessage"),
            "tool":         getattr(tools_mod, "tool"),
            "StateGraph":   getattr(graph_mod, "StateGraph"),
            "END":          getattr(graph_mod, "END"),
        }
    except Exception as exc:
        raise RuntimeError(f"Slack agent dependencies missing: {exc}") from exc


def _get_llm(model_override: Optional[str] = None, user_id: Optional[str] = None):
    from ..llm_factory import get_llm
    kwargs: Dict = {}
    if user_id:
        kwargs["user_id"] = user_id
    if model_override:
        kwargs["model"] = model_override
    return get_llm(**kwargs)


# ── PostgreSQL helpers ────────────────────────────────────────────────────────

def _get_conn():
    from ..db import _get_conn as _conn  # type: ignore
    return _conn()


def _row_to_dict(row, description) -> dict:
    return {col.name: val for col, val in zip(description, row)}


def _fetch_recent_db_messages(user_id: str, limit: int = 15, channel_name: Optional[str] = None) -> List[Dict]:
    """Fetch recent Slack messages for a user from PostgreSQL (7-day window)."""
    conn = _get_conn()
    try:
        cur = conn.cursor()
        if channel_name:
            cur.execute(
                """
                SELECT id, user_id, slack_user_id, slack_channel_id, channel_name, text, ts,
                       thread_ts, message_type, created_at
                FROM public.slack_messages
                WHERE user_id = %s
                  AND created_at > NOW() - INTERVAL '7 days'
                  AND (LOWER(channel_name) = LOWER(%s) OR slack_channel_id = %s)
                ORDER BY created_at DESC
                LIMIT %s
                """,
                (user_id, channel_name, channel_name, limit),
            )
        else:
            cur.execute(
                """
                SELECT id, user_id, slack_user_id, slack_channel_id, channel_name, text, ts,
                       thread_ts, message_type, created_at
                FROM public.slack_messages
                WHERE user_id = %s
                  AND created_at > NOW() - INTERVAL '7 days'
                ORDER BY created_at DESC
                LIMIT %s
                """,
                (user_id, limit),
            )
        rows  = cur.fetchall()
        msgs  = [_row_to_dict(r, cur.description) for r in rows]
        cur.close()
        return msgs
    except Exception as exc:
        log.warning("_fetch_recent_db_messages failed: %s", exc)
        return []
    finally:
        conn.close()


def _insert_task_from_slack(user_id: str, title: str, priority: str = "medium",
                             due_date: Optional[str] = None, slack_ts: Optional[str] = None) -> Optional[Dict]:
    """Insert a task into public.tasks with source_name='Slack'."""
    conn = _get_conn()
    try:
        cur = conn.cursor()
        due = None
        if due_date:
            try:
                due = datetime.fromisoformat(due_date.replace("Z", "+00:00"))
            except Exception:
                pass

        ext = f"slack:{slack_ts}" if slack_ts else None
        cur.execute(
            """
            INSERT INTO public.tasks
                (user_id, title, status, priority, due_date, source_name, source_logo, external_ref, position)
            VALUES (%s, %s, 'planned', %s, %s, 'Slack', 'slack', %s, 0)
            ON CONFLICT (user_id, external_ref) WHERE external_ref IS NOT NULL
            DO UPDATE SET
                title = EXCLUDED.title,
                priority = EXCLUDED.priority,
                due_date = EXCLUDED.due_date,
                updated_at = NOW()
            RETURNING id, user_id, title, status, priority, due_date, source_name, external_ref, created_at
            """,
            (user_id, title, priority, due, ext),
        )
        row  = cur.fetchone()
        task = _row_to_dict(row, cur.description) if row else {}
        conn.commit()
        cur.close()
        return task
    except Exception as exc:
        log.warning("_insert_task_from_slack failed: %s", exc)
        conn.rollback()
        return None
    finally:
        conn.close()


def _list_slack_tasks(user_id: str, limit: int = 10) -> List[Dict]:
    """List tasks created from Slack for a user."""
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, title, status, priority, due_date, source_name, external_ref, created_at
            FROM public.tasks
            WHERE user_id = %s AND source_name = 'Slack'
            ORDER BY created_at DESC
            LIMIT %s
            """,
            (user_id, limit),
        )
        rows  = cur.fetchall()
        tasks = [_row_to_dict(r, cur.description) for r in rows]
        cur.close()
        return tasks
    except Exception as exc:
        log.warning("_list_slack_tasks failed: %s", exc)
        return []
    finally:
        conn.close()


# ── Slack SDK helper ──────────────────────────────────────────────────────────

def _get_slack_client():
    """Return a Slack WebClient if SLACK_BOT_TOKEN is configured."""
    bot_token = os.getenv("SLACK_BOT_TOKEN", "").strip()
    if not bot_token or bot_token.startswith("xoxb-placeholder"):
        return None
    try:
        from slack_sdk import WebClient  # type: ignore
        return WebClient(token=bot_token)
    except ImportError:
        log.warning("slack_sdk not installed - Slack send actions disabled.")
        return None


def _send_slack_message_sdk(channel_name: str, text: str) -> Tuple[bool, str]:
    """Send a message via Slack Web API. Returns (success, detail)."""
    client = _get_slack_client()
    if not client:
        return False, "Slack bot token not configured. Add SLACK_BOT_TOKEN to .env."

    try:
        # Resolve channel id from name
        from slack_sdk.errors import SlackApiError  # type: ignore
        name = channel_name.lstrip("#").lower()
        resp = client.conversations_list(types="public_channel,private_channel", limit=300, exclude_archived=True)
        channel_id = next(
            (ch["id"] for ch in resp["channels"] if ch["name"].lower() == name),
            None,
        )
        if not channel_id:
            return False, f"Channel #{channel_name} not found."
        client.chat_postMessage(channel=channel_id, text=text)
        return True, f"Message sent to #{channel_name}"
    except SlackApiError as exc:
        return False, f"Slack API error: {exc.response['error']}"
    except Exception as exc:
        return False, str(exc)


# ── Tool factory ──────────────────────────────────────────────────────────────

def _slack_toolset(tool_decorator, user_id: str):

    @tool_decorator
    def search_slack_messages(query: str, limit: int = 8) -> str:
        """Semantic search over the user's recent Slack messages stored in Qdrant.
        Use this to answer questions like 'what was discussed in #general?' or
        'find Slack messages about the release deadline'."""
        try:
            from .qdrant_store import search_messages  # type: ignore
            results = search_messages(user_id=user_id, query=query, limit=max(1, min(limit, 20)))
            if not results:
                return "No relevant Slack messages found."
            lines = [f"[{r['channel_name'] or 'unknown'}] {r['text'][:200]} ({r['created_at'][:10]})"
                     for r in results]
            return "Relevant Slack messages:\n" + "\n".join(lines)
        except Exception as exc:
            return f"Search error: {exc}"

    @tool_decorator
    def get_recent_messages(channel: str = "", limit: int = 10) -> str:
        """Fetch the most recent Slack messages (up to 7 days old).
        Optionally filter by channel name (without #).
        Use this when the user asks to 'show messages from #standup' or 'what's new in Slack'."""
        try:
            safe_limit = max(1, min(limit, 30))
            msgs = _fetch_recent_db_messages(
                user_id=user_id,
                limit=safe_limit,
                channel_name=channel.lstrip("#") if channel else None,
            )
            if not msgs:
                return "No recent Slack messages found (last 7 days)."
            lines = [
                f"[{m['channel_name'] or m['slack_channel_id']}] {m['text'] or '(empty)'} "
                f"- {str(m['created_at'])[:16]}"
                for m in msgs
            ]
            return f"Recent messages ({len(lines)}):\n" + "\n".join(lines)
        except Exception as exc:
            return f"Error fetching messages: {exc}"

    @tool_decorator
    def send_slack_message(channel: str, text: str) -> str:
        """Send a message to a Slack channel.
        channel: channel name without # (e.g. 'general').
        text: the message content to post."""
        if not channel or not text:
            return "Both channel and text are required."
        ok, detail = _send_slack_message_sdk(channel, text)
        return detail

    @tool_decorator
    def create_task_from_slack(
        title: str,
        priority: str = "medium",
        due_date: str = "",
        slack_ts: str = "",
    ) -> str:
        """Create a task in NUMA from a Slack message or discussion.
        title: short task description (imperative verb, e.g. 'Review PR #42').
        priority: low | medium | high | urgent.
        due_date: ISO-8601 date (YYYY-MM-DD) or empty.
        slack_ts: Slack message timestamp for deduplication (optional)."""
        if not title.strip():
            return "Task title is required."
        valid_priorities = {"low", "medium", "high", "urgent"}
        pri = priority.strip().lower() if priority.strip().lower() in valid_priorities else "medium"
        task = _insert_task_from_slack(
            user_id=user_id,
            title=title.strip(),
            priority=pri,
            due_date=due_date.strip() or None,
            slack_ts=slack_ts.strip() or None,
        )
        if task:
            return f"Task created: \"{task.get('title')}\" [{task.get('priority')}] (id={task.get('id')})"
        return "Failed to create task. Please try again."

    @tool_decorator
    def list_slack_tasks(limit: int = 10) -> str:
        """List tasks in NUMA that were created from Slack messages."""
        tasks = _list_slack_tasks(user_id=user_id, limit=max(1, min(limit, 30)))
        if not tasks:
            return "No Slack-sourced tasks found."
        lines = [
            f"• {t['title']} [{t['status']} / {t['priority']}]"
            + (f" due {t['due_date']}" if t.get("due_date") else "")
            for t in tasks
        ]
        return f"Slack tasks ({len(lines)}):\n" + "\n".join(lines)

    return [
        search_slack_messages,
        get_recent_messages,
        send_slack_message,
        create_task_from_slack,
        list_slack_tasks,
    ]


# ── LangGraph build ───────────────────────────────────────────────────────────

from functools import lru_cache

@lru_cache(maxsize=64)
def _build_slack_graph(user_id: str, model_override: Optional[str] = None):
    deps = _require_deps()

    AIMessage    = deps["AIMessage"]
    SystemMessage = deps["SystemMessage"]
    ToolMessage  = deps["ToolMessage"]
    StateGraph   = deps["StateGraph"]
    END          = deps["END"]

    tools    = _slack_toolset(deps["tool"], user_id)
    tool_map = {t.name: t for t in tools}
    mutation_tools = {"create_task_from_slack", "send_slack_message"}

    def call_model(state: SlackAgentState) -> SlackAgentState:
        llm = _get_llm(model_override=model_override, user_id=user_id)
        llm_with_tools = llm.bind_tools(tools)

        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        sem = (state.get("semantic_context") or "").strip()
        context_block = f"\nRelevant context from memory:\n{sem}\n" if sem else ""

        system = (
            f"{SLACK_AGENT_SYSTEM_PROMPT}\n"
            f"Current time: {now}"
            f"{context_block}"
        )
        full_messages = [SystemMessage(content=system)] + list(state["messages"])
        response = llm_with_tools.invoke(full_messages)
        return {
            "messages":         [response],
            "user_query":       state["user_query"],
            "user_id":          state["user_id"],
            "semantic_context": state["semantic_context"],
            "mutated":          state["mutated"],
        }

    def call_tools(state: SlackAgentState) -> SlackAgentState:
        last   = state["messages"][-1]
        out    = []
        mutated = state["mutated"]
        for tc in getattr(last, "tool_calls", []):
            name     = tc.get("name")
            args     = tc.get("args", {})
            tool_id  = tc.get("id")
            if name not in tool_map:
                result = f"Unknown tool '{name}'."
            else:
                try:
                    result = tool_map[name].invoke(args)
                    if name in mutation_tools and not str(result).lower().startswith("error"):
                        mutated = True
                except Exception as exc:
                    result = f"Error running {name}: {exc}"
            out.append(ToolMessage(content=str(result), tool_call_id=tool_id))
        return {
            "messages":         out,
            "user_query":       state["user_query"],
            "user_id":          state["user_id"],
            "semantic_context": state["semantic_context"],
            "mutated":          mutated,
        }

    def should_continue(state: SlackAgentState):
        last = state["messages"][-1]
        rounds = sum(
            1 for m in state["messages"]
            if hasattr(m, "tool_calls") and m.tool_calls
        )
        if rounds >= 6:
            return "end"
        if hasattr(last, "tool_calls") and last.tool_calls:
            return "call_tools"
        return "end"

    wf = StateGraph(SlackAgentState)
    wf.add_node("call_model", call_model)
    wf.add_node("call_tools", call_tools)
    wf.set_entry_point("call_model")
    wf.add_conditional_edges("call_model", should_continue, {"call_tools": "call_tools", "end": END})
    wf.add_edge("call_tools", "call_model")
    return wf.compile(), AIMessage


# ── Public entry point ────────────────────────────────────────────────────────

def run_slack_agent_chat(
    query: str,
    history: List[dict],
    user_id: Optional[str],
    model: Optional[str] = None,
) -> Dict:
    """Invoke the Slack sub-agent and return a response dict.

    Returns
    -------
    {
        "response":      str,
        "success":       bool,
        "delegated_to":  "slack-subagent",
        "refresh_slack": bool,
    }
    """
    if not user_id:
        return {
            "response":      "User session is missing. Please sign in again.",
            "success":       False,
            "delegated_to":  "slack-subagent",
            "refresh_slack": False,
        }

    from ..llm_factory import is_any_llm_configured
    if not is_any_llm_configured(user_id):
        return {
            "response": (
                "Slack sub-agent is unavailable - no LLM provider is configured. "
                "Go to Settings and add an API key for your preferred AI provider."
            ),
            "success":       True,
            "delegated_to":  "slack-subagent",
            "refresh_slack": False,
        }

    try:
        deps          = _require_deps()
        HumanMessage  = deps["HumanMessage"]
        AIMessage     = deps["AIMessage"]

        # Build semantic context from shared memory service
        try:
            from ..memory.service import memory_service  # type: ignore
            semantic_context = memory_service.build_context_for_query(user_id, query)
        except Exception:
            semantic_context = ""

        graph, AIMsg = _build_slack_graph(user_id, model)

        # Convert history
        history_messages: List[object] = []
        for m in history:
            content = (m.get("content") or "").strip()
            if not content:
                continue
            role = (m.get("role") or "").lower()
            if role == "user":
                history_messages.append(HumanMessage(content=content))
            elif role in ("assistant", "ai"):
                history_messages.append(AIMessage(content=content))

        initial_state: SlackAgentState = {
            "messages":         history_messages + [HumanMessage(content=query)],
            "user_query":       query,
            "user_id":          user_id,
            "semantic_context": semantic_context,
            "mutated":          False,
        }

        result    = graph.invoke(initial_state)
        messages  = result.get("messages", [])
        if not messages:
            raise RuntimeError("No response produced by Slack sub-agent")

        final   = messages[-1]
        content = getattr(final, "content", str(final))
        if isinstance(content, list):
            content = "\n".join(str(part) for part in content)

        mutated = bool(result.get("mutated", False))

        # Store in shared semantic memory
        if user_id and str(content).strip():
            try:
                from ..memory.service import memory_service  # type: ignore
                memory_service.store_turn(user_id, query, str(content))
            except Exception:
                pass

        return {
            "response":      str(content),
            "success":       True,
            "delegated_to":  "slack-subagent",
            "refresh_slack": mutated,
        }

    except Exception as exc:
        log.error("Slack sub-agent error: %s", exc, exc_info=True)
        return {
            "response":      f"Slack sub-agent encountered an error: {exc}",
            "success":       False,
            "delegated_to":  "slack-subagent",
            "refresh_slack": False,
        }
