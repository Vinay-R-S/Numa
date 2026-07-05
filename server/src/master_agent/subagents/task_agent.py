"""Task sub-agent: toolset, LangGraph build, and run entrypoint
(NUMA-106 P3, PLAN 16.3).

Extracted verbatim from master_agent/service.py; service.py re-exports these
names so existing import paths keep working.
"""
from datetime import datetime, timezone
from functools import lru_cache
from typing import List, Optional, Tuple

from ..common import (
    _get_llm,
    _history_to_messages,
    _parse_due_datetime,
    _require_master_dependencies,
)
from ..state import TaskAgentState
from ...memory import memory_service
from ...tasks import service as task_service


TASK_SUBAGENT_SYSTEM_PROMPT = (
    "You are NUMA Task sub-agent. "
    "You can only operate through tools to create, update, delete, and list tasks. "
    "If required details are missing, ask a short clarification question. "
    "Never invent task IDs or claim updates you did not perform. "
    "For card moves, update status only. Do not delete and recreate the task. "
    "For a request to add one task, call create_task exactly once. "
    "Do not use emojis."
)


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
