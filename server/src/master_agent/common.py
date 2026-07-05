"""Shared master-agent helpers: dependency loading, LLM access, message and
datetime parsing (NUMA-106 P3, PLAN 16.3).

Extracted verbatim from master_agent/service.py; service.py re-exports these
names so existing import paths keep working.
"""
import importlib
from datetime import datetime, timezone
from typing import Dict, List, Optional


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


def _format_local_time(value) -> str:
    if isinstance(value, datetime):
        return value.strftime("%H:%M")
    return str(value or "")
