"""
GitHub Sub-Agent Service - LangGraph agentic loop for GitHub queries.

Tools:
  check_commits       - count commits today/this week
  get_pr_status       - list open PRs
  get_repo_stats      - recent repos with stars/forks
  get_contribution_overview - full stats summary

Entry point:
  run_github_agent_chat(query, history, user_id, model=None) -> Dict
"""
from __future__ import annotations

import importlib
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Annotated, Dict, List, Optional, Sequence, TypedDict

import operator

log = logging.getLogger(__name__)

GITHUB_AGENT_SYSTEM_PROMPT = (
    "You are NUMA GitHub sub-agent. You help users understand their GitHub activity - "
    "commits, pull requests, repositories, and contribution stats. "
    "Always use tools to fetch real data from the GitHub API - never fabricate numbers. "
    "If GitHub is not connected, guide users to Settings to connect their account. "
    "Keep responses concise and developer-friendly. Do not use emojis. Use plain Markdown when structure helps."
)


class GitHubAgentState(TypedDict):
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
        raise RuntimeError(f"GitHub agent dependencies missing: {exc}") from exc


def _get_llm(model_override: Optional[str] = None, user_id: Optional[str] = None):
    from ..llm_factory import get_llm_with_fallback
    return get_llm_with_fallback(
        user_id=user_id,
        agent_name="github",
        priority="normal",
        model=model_override,
    )


def _github_toolset(tool_decorator, user_id: str):
    from .router import _get_github_token, _get_github_username
    from ..tasks.agent_tools import make_task_tools

    def _get_client():
        token = _get_github_token(user_id)
        if not token:
            return None
        from .github_client import GitHubClient
        return GitHubClient(token)

    @tool_decorator
    def check_commits(period: str = "today") -> str:
        """Check how many commits the user made today or this week.
        period: 'today' or 'week'."""
        client = _get_client()
        if not client:
            return "GitHub not connected. Go to Settings → Connect GitHub."
        username = _get_github_username(user_id)
        if not username:
            return "GitHub username not found."

        now = datetime.now(timezone.utc)
        if period == "week":
            since = now - timedelta(days=7)
            label = "this week"
        else:
            since = now.replace(hour=0, minute=0, second=0, microsecond=0)
            label = "today"

        count = client.get_commits_count(username, since)
        return f"You have {count} commit(s) {label}."

    @tool_decorator
    def get_pr_status() -> str:
        """Get the user's open pull requests across all repos."""
        client = _get_client()
        if not client:
            return "GitHub not connected."
        username = _get_github_username(user_id)
        if not username:
            return "GitHub username not found."

        prs = client.get_open_prs(username)
        if not prs:
            return "No open pull requests."
        lines = [f"Open PRs ({len(prs)}):"]
        for pr in prs:
            lines.append(f"  - {pr['title']} in {pr['repo']} ({pr['html_url']})")
        return "\n".join(lines)

    @tool_decorator
    def get_repo_stats(count: int = 5) -> str:
        """Get the user's most recently updated repositories with stats."""
        client = _get_client()
        if not client:
            return "GitHub not connected."
        repos = client.get_repos(per_page=min(count, 15))
        if not repos:
            return "No repositories found."
        lines = [f"Recent repos ({len(repos)}):"]
        for r in repos:
            vis = "private" if r["private"] else "public"
            lines.append(
                f"  - {r['full_name']} ({vis}) | "
                f"{r.get('language') or 'N/A'} | "
                f"stars {r['stars']} | forks {r['forks']}"
            )
        return "\n".join(lines)

    @tool_decorator
    def get_contribution_overview() -> str:
        """Get a full overview of the user's GitHub contributions: commits, PRs, repos, followers."""
        client = _get_client()
        if not client:
            return "GitHub not connected."
        username = _get_github_username(user_id)
        if not username:
            return "GitHub username not found."

        stats = client.get_contribution_stats(username)
        try:
            from .router import _store_github_stats_vector
            _store_github_stats_vector(user_id, stats)
        except Exception:
            pass
        lines = [
            f"GitHub: @{stats['username']}",
            f"  Repos: {stats['public_repos']} public, {stats['private_repos']} private",
            f"  Followers: {stats['followers']} | Following: {stats['following']}",
            f"  Commits today: {stats['total_commits_today']}",
            f"  Commits this week: {stats['total_commits_week']}",
            f"  Open PRs: {stats['open_prs']}",
        ]
        return "\n".join(lines)

    task_tools = make_task_tools(tool_decorator, user_id, source_name="GitHub")
    return [check_commits, get_pr_status, get_repo_stats, get_contribution_overview] + task_tools


from functools import lru_cache


@lru_cache(maxsize=64)
def _build_github_graph(user_id: str, model_override: Optional[str] = None):
    deps = _require_deps()
    AIMessage = deps["AIMessage"]
    SystemMessage = deps["SystemMessage"]
    ToolMessage = deps["ToolMessage"]
    StateGraph = deps["StateGraph"]
    END = deps["END"]

    tools = _github_toolset(deps["tool"], user_id)
    tool_map = {t.name: t for t in tools}

    def call_model(state: GitHubAgentState) -> GitHubAgentState:
        llm = _get_llm(model_override=model_override, user_id=user_id)
        llm_with_tools = llm.bind_tools(tools)
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        sem = (state.get("semantic_context") or "").strip()
        ctx = f"\nRelevant context:\n{sem}\n" if sem else ""
        system = f"{GITHUB_AGENT_SYSTEM_PROMPT}\nCurrent time: {now}{ctx}"
        full = [SystemMessage(content=system)] + list(state["messages"])
        response = llm_with_tools.invoke(full)
        return {**state, "messages": [response]}

    def call_tools(state: GitHubAgentState) -> GitHubAgentState:
        last = state["messages"][-1]
        out = []
        mutated = state["mutated"]
        for tc in getattr(last, "tool_calls", []):
            name, args, tid = tc.get("name"), tc.get("args", {}), tc.get("id")
            if name not in tool_map:
                result = f"Unknown tool '{name}'."
            else:
                try:
                    result = tool_map[name].invoke(args)
                except Exception as exc:
                    result = f"Error: {exc}"
            out.append(ToolMessage(content=str(result), tool_call_id=tid))
        return {**state, "messages": out, "mutated": mutated}

    def should_continue(state: GitHubAgentState):
        last = state["messages"][-1]
        rounds = sum(1 for m in state["messages"] if hasattr(m, "tool_calls") and m.tool_calls)
        if rounds >= 6:
            return "end"
        if hasattr(last, "tool_calls") and last.tool_calls:
            return "call_tools"
        return "end"

    wf = StateGraph(GitHubAgentState)
    wf.add_node("call_model", call_model)
    wf.add_node("call_tools", call_tools)
    wf.set_entry_point("call_model")
    wf.add_conditional_edges("call_model", should_continue, {"call_tools": "call_tools", "end": END})
    wf.add_edge("call_tools", "call_model")
    return wf.compile(), AIMessage


def run_github_agent_chat(
    query: str,
    history: List[dict],
    user_id: Optional[str],
    model: Optional[str] = None,
    preloaded_context: Optional[str] = None,
) -> Dict:
    if not user_id:
        return {"response": "User session is missing.", "success": False,
                "delegated_to": "github-subagent", "refresh_github": False}

    from ..llm_factory import is_any_llm_configured
    if not is_any_llm_configured(user_id):
        return {"response": "GitHub sub-agent unavailable - no LLM configured. Go to Settings.",
                "success": True, "delegated_to": "github-subagent", "refresh_github": False}

    try:
        deps = _require_deps()
        HumanMessage = deps["HumanMessage"]
        AIMessage = deps["AIMessage"]

        try:
            from ..memory.service import memory_service
            if preloaded_context:
                semantic_context = preloaded_context
            else:
                try:
                    from ..context_assembler import assemble_context
                    from ..data_planner import RetrievalPlan

                    plan = RetrievalPlan(
                        query=query,
                        temporal_scope="week",
                        domains=["github"],
                        qdrant_collections=["github", "tasks", "memory"],
                        days_per_domain={"github": 7, "tasks": 7},
                        token_budget={"github": 2200, "tasks": 1000, "memory": 800},
                    )
                    semantic_context = assemble_context(user_id, plan).text
                except Exception:
                    semantic_context = memory_service.build_context_for_query(user_id, query)
        except Exception:
            semantic_context = ""

        graph, _ = _build_github_graph(user_id, model)

        history_messages = []
        for m in history:
            content = (m.get("content") or "").strip()
            if not content:
                continue
            role = (m.get("role") or "").lower()
            if role == "user":
                history_messages.append(HumanMessage(content=content))
            elif role in ("assistant", "ai"):
                history_messages.append(AIMessage(content=content))

        initial_state: GitHubAgentState = {
            "messages": history_messages + [HumanMessage(content=query)],
            "user_query": query,
            "user_id": user_id,
            "semantic_context": semantic_context,
            "mutated": False,
        }

        result = graph.invoke(initial_state)
        messages = result.get("messages", [])
        if not messages:
            raise RuntimeError("No response from GitHub sub-agent")

        final = messages[-1]
        content = getattr(final, "content", str(final))
        if isinstance(content, list):
            content = "\n".join(str(p) for p in content)

        if user_id and str(content).strip():
            try:
                from ..memory.service import memory_service
                memory_service.store_turn(user_id, query, str(content))
            except Exception:
                pass

        return {
            "response": str(content),
            "success": True,
            "delegated_to": "github-subagent",
            "refresh_github": bool(result.get("mutated", False)),
        }
    except Exception as exc:
        log.error("GitHub sub-agent error: %s", exc, exc_info=True)
        return {
            "response": f"GitHub sub-agent error: {exc}",
            "success": False,
            "delegated_to": "github-subagent",
            "refresh_github": False,
        }
