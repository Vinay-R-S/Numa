"""
LeetCode Sub-Agent Service
============================
LangGraph agentic loop for LeetCode-related queries.

Tools:
  get_leetcode_stats   - fetch full LeetCode profile stats
  get_recent_solved    - recent accepted submissions

Entry point:
  run_leetcode_agent_chat(query, history, user_id, model=None) -> Dict
"""
from __future__ import annotations

import importlib
import logging
from datetime import datetime, timezone
from functools import lru_cache
from typing import Annotated, Dict, List, Optional, Sequence, TypedDict

import operator

log = logging.getLogger(__name__)

LEETCODE_AGENT_SYSTEM_PROMPT = (
    "You are NUMA LeetCode sub-agent. You help users track and analyze their "
    "LeetCode progress. You can fetch profile stats (total solved, difficulty "
    "breakdown, ranking) and recent accepted submissions. "
    "Always use tools to fetch real data - never fabricate stats or problem names. "
    "If a username is not provided, ask the user for it. "
    "Keep responses concise, encouraging, and coding-focused. Do not use emojis. Use plain Markdown when structure helps."
)


class LeetCodeAgentState(TypedDict):
    messages: Annotated[Sequence[object], operator.add]
    user_query: str
    user_id: str
    semantic_context: str
    mutated: bool


def _require_deps() -> Dict:
    try:
        msgs_mod = importlib.import_module("langchain_core.messages")
        tools_mod = importlib.import_module("langchain_core.tools")
        graph_mod = importlib.import_module("langgraph.graph")
        return {
            "AIMessage": getattr(msgs_mod, "AIMessage"),
            "HumanMessage": getattr(msgs_mod, "HumanMessage"),
            "SystemMessage": getattr(msgs_mod, "SystemMessage"),
            "ToolMessage": getattr(msgs_mod, "ToolMessage"),
            "tool": getattr(tools_mod, "tool"),
            "StateGraph": getattr(graph_mod, "StateGraph"),
            "END": getattr(graph_mod, "END"),
        }
    except Exception as exc:
        raise RuntimeError(f"LeetCode agent dependencies missing: {exc}") from exc


def _get_llm(model_override: Optional[str] = None, user_id: Optional[str] = None):
    from ..llm_factory import get_llm_with_fallback
    return get_llm_with_fallback(
        user_id=user_id,
        agent_name="leetcode",
        priority="normal",
        model=model_override,
    )


def _leetcode_toolset(tool_decorator, user_id: str):
    from .leetcode_client import LeetCodeClient
    from ..tasks.agent_tools import make_task_tools

    client = LeetCodeClient()

    @tool_decorator
    def get_leetcode_stats(username: str) -> str:
        """Fetch full LeetCode profile stats for a user: total solved, difficulty
        breakdown (easy/medium/hard), acceptance rate, ranking, and reputation.
        Use this when the user asks about their LeetCode profile, progress, or stats."""
        try:
            stats = client.get_full_stats(username)
            lines = [
                f"LeetCode Stats for {stats['username']}:",
                f"  Total Solved: {stats['total_solved']}",
                f"  Easy: {stats['easy_solved']} | Medium: {stats['medium_solved']} | Hard: {stats['hard_solved']}",
                f"  Acceptance Rate: {stats['acceptance_rate']}%",
                f"  Ranking: {stats['ranking']:,}",
                f"  Reputation: {stats['reputation']}",
            ]
            recent = stats.get("recent_submissions", [])
            if recent:
                lines.append(f"  Recent Accepted ({len(recent)}):")
                for s in recent[:5]:
                    lines.append(f"    - {s['title']} ({s['lang']}) - {s['status']}")
            return "\n".join(lines)
        except ValueError as exc:
            return str(exc)
        except Exception as exc:
            return f"Error fetching LeetCode stats: {exc}"

    @tool_decorator
    def get_recent_solved(username: str, count: int = 10) -> str:
        """Fetch recent accepted LeetCode submissions for a user.
        Use this when the user asks what problems they solved recently."""
        try:
            safe_count = max(1, min(count, 20))
            submissions = client.get_recent_submissions(username, limit=safe_count)
            if not submissions:
                return f"No recent accepted submissions found for '{username}'."
            lines = [f"Recent Accepted Submissions for {username} ({len(submissions)}):"]
            for s in submissions:
                ts = s.get("timestamp", "")
                title = s.get("title", "Untitled")
                lang = s.get("lang", "?")
                lines.append(f"  - {title} ({lang}) - ts:{ts}")
            return "\n".join(lines)
        except ValueError as exc:
            return str(exc)
        except Exception as exc:
            return f"Error fetching recent submissions: {exc}"

    task_tools = make_task_tools(tool_decorator, user_id, source_name="LeetCode")
    return [get_leetcode_stats, get_recent_solved] + task_tools


@lru_cache(maxsize=64)
def _build_leetcode_graph(user_id: str, model_override: Optional[str] = None):
    deps = _require_deps()
    AIMessage = deps["AIMessage"]
    SystemMessage = deps["SystemMessage"]
    ToolMessage = deps["ToolMessage"]
    StateGraph = deps["StateGraph"]
    END = deps["END"]

    tools = _leetcode_toolset(deps["tool"], user_id)
    tool_map = {t.name: t for t in tools}

    def call_model(state: LeetCodeAgentState) -> LeetCodeAgentState:
        llm = _get_llm(model_override=model_override, user_id=user_id)
        llm_with_tools = llm.bind_tools(tools)
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        sem = (state.get("semantic_context") or "").strip()
        context = f"\nRelevant context from memory:\n{sem}\n" if sem else ""
        system = f"{LEETCODE_AGENT_SYSTEM_PROMPT}\nCurrent time: {now}{context}"
        full = [SystemMessage(content=system)] + list(state["messages"])
        response = llm_with_tools.invoke(full)
        return {**state, "messages": [response]}

    def call_tools(state: LeetCodeAgentState) -> LeetCodeAgentState:
        last = state["messages"][-1]
        out = []
        for tc in getattr(last, "tool_calls", []):
            name, args, tid = tc.get("name"), tc.get("args", {}), tc.get("id")
            if name not in tool_map:
                result = f"Unknown tool '{name}'."
            else:
                try:
                    result = tool_map[name].invoke(args)
                except Exception as exc:
                    result = f"Error running {name}: {exc}"
            out.append(ToolMessage(content=str(result), tool_call_id=tid))
        return {**state, "messages": out}

    def should_continue(state: LeetCodeAgentState):
        last = state["messages"][-1]
        rounds = sum(1 for m in state["messages"] if hasattr(m, "tool_calls") and m.tool_calls)
        if rounds >= 6:
            return "end"
        if hasattr(last, "tool_calls") and last.tool_calls:
            return "call_tools"
        return "end"

    wf = StateGraph(LeetCodeAgentState)
    wf.add_node("call_model", call_model)
    wf.add_node("call_tools", call_tools)
    wf.set_entry_point("call_model")
    wf.add_conditional_edges("call_model", should_continue, {"call_tools": "call_tools", "end": END})
    wf.add_edge("call_tools", "call_model")
    return wf.compile(), AIMessage


def run_leetcode_agent_chat(
    query: str,
    history: List[dict],
    user_id: Optional[str],
    model: Optional[str] = None,
    preloaded_context: Optional[str] = None,
) -> Dict:
    """Invoke the LeetCode sub-agent and return a response dict."""
    if not user_id:
        return {
            "response": "User session is missing. Please sign in again.",
            "success": False,
            "delegated_to": "leetcode-subagent",
        }

    from ..llm_factory import is_any_llm_configured
    if not is_any_llm_configured(user_id):
        return {
            "response": (
                "LeetCode sub-agent is unavailable - no LLM provider is configured. "
                "Go to Settings and add an API key for your preferred AI provider."
            ),
            "success": True,
            "delegated_to": "leetcode-subagent",
        }

    try:
        deps = _require_deps()
        HumanMessage = deps["HumanMessage"]
        AIMessage = deps["AIMessage"]

        try:
            from ..memory.service import memory_service
            if preloaded_context:
                semantic_context = preloaded_context
            else:
                semantic_context = memory_service.build_context_for_query(user_id, query)
        except Exception:
            semantic_context = ""

        graph, _ = _build_leetcode_graph(user_id, model)

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

        initial_state: LeetCodeAgentState = {
            "messages": history_messages + [HumanMessage(content=query)],
            "user_query": query,
            "user_id": user_id,
            "semantic_context": semantic_context,
            "mutated": False,
        }

        result = graph.invoke(initial_state)
        messages = result.get("messages", [])
        if not messages:
            raise RuntimeError("No response produced by LeetCode sub-agent")

        final = messages[-1]
        content = getattr(final, "content", str(final))
        if isinstance(content, list):
            content = "\n".join(str(part) for part in content)

        if user_id and str(content).strip():
            try:
                from ..memory.service import memory_service
                memory_service.store_turn(user_id, query, str(content))
            except Exception:
                pass

        return {
            "response": str(content),
            "success": True,
            "delegated_to": "leetcode-subagent",
        }

    except Exception as exc:
        log.error("LeetCode sub-agent error: %s", exc, exc_info=True)
        return {
            "response": f"LeetCode sub-agent encountered an error: {exc}",
            "success": False,
            "delegated_to": "leetcode-subagent",
        }
