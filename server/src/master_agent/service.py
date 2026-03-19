import importlib
import json
import operator
import os
import re
from datetime import datetime, timezone
from functools import lru_cache
from typing import Annotated, Dict, List, Optional, Sequence, Tuple, TypedDict

from ..calendar_agent.service import run_agent_chat
from ..memory import memory_service
from ..tasks import service as task_service


MASTER_ROUTER_PROMPT = (
    "You are NUMA master agent router. "
    "Choose exactly one route for the user's request: calendar, tasks, or general. "
    "Return strict JSON only with shape: {\"route\":\"calendar|tasks|general\",\"reason\":\"short\"}. "
    "Use calendar for meeting/event/calendar operations. "
    "Use tasks for task list operations. "
    "Use general for small talk or questions that do not require tool actions."
)

TASK_SUBAGENT_SYSTEM_PROMPT = (
    "You are NUMA Task sub-agent. "
    "You can only operate through tools to create, update, delete, and list tasks. "
    "If required details are missing, ask a short clarification question. "
    "Never invent task IDs or claim updates you did not perform."
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


def _require_master_dependencies() -> Dict[str, object]:
    try:
        messages_module = importlib.import_module("langchain_core.messages")
        tools_module = importlib.import_module("langchain_core.tools")
        groq_module = importlib.import_module("langchain_groq")
        graph_module = importlib.import_module("langgraph.graph")

        return {
            "AIMessage": getattr(messages_module, "AIMessage"),
            "HumanMessage": getattr(messages_module, "HumanMessage"),
            "SystemMessage": getattr(messages_module, "SystemMessage"),
            "ToolMessage": getattr(messages_module, "ToolMessage"),
            "tool": getattr(tools_module, "tool"),
            "ChatGroq": getattr(groq_module, "ChatGroq"),
            "StateGraph": getattr(graph_module, "StateGraph"),
            "END": getattr(graph_module, "END"),
        }
    except Exception as exc:
        raise RuntimeError(
            "Master agent dependencies are missing. Install langchain, langgraph, langchain-core, and langchain-groq."
        ) from exc


def _get_llm(chat_groq_cls):
    api_key = os.getenv("GROQ_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("GROQ_API_KEY is not configured")

    model = os.getenv("GROQ_MASTER_MODEL", os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"))
    temperature = float(os.getenv("GROQ_MASTER_TEMPERATURE", "0.1"))
    return chat_groq_cls(model=model, temperature=temperature, api_key=api_key)


def _extract_json_object(text: str) -> Dict:
    content = (text or "").strip()
    if not content:
        return {}

    try:
        return json.loads(content)
    except Exception:
        pass

    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", content, flags=re.S)
    if fenced:
        try:
            return json.loads(fenced.group(1))
        except Exception:
            pass

    first = content.find("{")
    last = content.rfind("}")
    if first != -1 and last != -1 and last > first:
        try:
            return json.loads(content[first : last + 1])
        except Exception:
            return {}

    return {}


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


def _invoke_json(llm, prompt: str, user_query: str, semantic_context: str = "") -> Dict:
    context_block = ""
    if semantic_context:
        context_block = (
            "\nRelevant semantic memory (user-scoped retrieved context):\n"
            f"{semantic_context}\n"
            "Use this only if relevant."
        )

    response = llm.invoke(f"{prompt}{context_block}\n\nUser request:\n{user_query}")
    content = getattr(response, "content", "")
    if isinstance(content, list):
        content = "\n".join(str(part) for part in content)
    return _extract_json_object(str(content))


def _route_query(query: str, semantic_context: str, llm) -> str:
    data = _invoke_json(llm, MASTER_ROUTER_PROMPT, query, semantic_context)
    route = str(data.get("route", "")).strip().lower()
    if route in {"calendar", "tasks", "general"}:
        return route

    q = query.lower()
    if any(word in q for word in ("calendar", "meeting", "event", "schedule", "reschedule")):
        return "calendar"
    if any(word in q for word in ("task", "todo", "to-do", "kanban", "list tasks")):
        return "tasks"
    return "general"


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


def _task_toolset(tool_decorator, user_id: str):
    @tool_decorator
    def create_task(
        title: str,
        description: str = "",
        status: str = "planned",
        due_datetime: str = "",
    ) -> str:
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
        try:
            deleted = task_service.delete_task_by_title(user_id=user_id, title=title.strip())
            if deleted == 0:
                return f"Task not found: {title}."
            return f"Task deleted: {title}."
        except Exception as exc:
            return f"Error deleting task: {exc}"

    @tool_decorator
    def list_tasks(limit: int = 10) -> str:
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
def _build_task_subagent_graph(user_id: str):
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
        llm = _get_llm(deps["ChatGroq"])
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
) -> Tuple[str, bool]:
    try:
        deps = _require_master_dependencies()
        HumanMessage = deps["HumanMessage"]
        AIMessage = deps["AIMessage"]

        graph, AIMessageType = _build_task_subagent_graph(user_id)

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
        "Mention that you can operate the Calendar sub-agent and Task sub-agent. "
        f"{context_block}\n\nUser: {query}"
    )
    response = llm.invoke(prompt)
    content = getattr(response, "content", "")
    if isinstance(content, list):
        content = "\n".join(str(part) for part in content)
    return str(content).strip() or "How can I help with your calendar or tasks?"


@lru_cache(maxsize=1)
def _build_master_graph():
    deps = _require_master_dependencies()
    StateGraph = deps["StateGraph"]
    END = deps["END"]

    def route_intent(state: MasterAgentState) -> Dict:
        llm = _get_llm(deps["ChatGroq"])
        route = _route_query(state["query"], state.get("semantic_context", ""), llm)
        return {"route": route}

    def delegate_calendar(state: MasterAgentState) -> Dict:
        delegated = run_agent_chat(
            query=state["query"],
            history=state.get("history", []),
            user_id=state["user_id"],
        )

        response_text = str(delegated.get("response", "Done."))
        success = bool(delegated.get("success", True))
        refresh_calendar = bool(delegated.get("refreshCalendar", False))

        if state["user_id"] and response_text.strip():
            memory_service.store_turn(state["user_id"], state["query"], response_text)

        return {
            "response": response_text,
            "success": success,
            "delegated_to": "calendar-subagent",
            "refreshCalendar": refresh_calendar,
            "refreshTasks": refresh_calendar,
        }

    def delegate_tasks(state: MasterAgentState) -> Dict:
        response_text, refresh_tasks = _run_task_subagent(
            query=state["query"],
            history=state.get("history", []),
            user_id=state["user_id"],
            semantic_context=state.get("semantic_context", ""),
        )

        return {
            "response": response_text,
            "success": not response_text.lower().startswith("error running task sub-agent:"),
            "delegated_to": "task-subagent",
            "refreshCalendar": False,
            "refreshTasks": refresh_tasks,
        }

    def answer_general(state: MasterAgentState) -> Dict:
        llm = _get_llm(deps["ChatGroq"])
        response_text = _answer_general(state["query"], state.get("semantic_context", ""), llm)

        if state["user_id"] and response_text.strip():
            memory_service.store_turn(state["user_id"], state["query"], response_text)

        return {
            "response": response_text,
            "success": True,
            "delegated_to": "master",
            "refreshCalendar": False,
            "refreshTasks": False,
        }

    def choose_route(state: MasterAgentState):
        route = str(state.get("route") or "general").lower()
        if route == "calendar":
            return "calendar"
        if route == "tasks":
            return "tasks"
        return "general"

    workflow = StateGraph(MasterAgentState)
    workflow.add_node("route_intent", route_intent)
    workflow.add_node("delegate_calendar", delegate_calendar)
    workflow.add_node("delegate_tasks", delegate_tasks)
    workflow.add_node("answer_general", answer_general)

    workflow.set_entry_point("route_intent")
    workflow.add_conditional_edges(
        "route_intent",
        choose_route,
        {
            "calendar": "delegate_calendar",
            "tasks": "delegate_tasks",
            "general": "answer_general",
        },
    )
    workflow.add_edge("delegate_calendar", END)
    workflow.add_edge("delegate_tasks", END)
    workflow.add_edge("answer_general", END)

    return workflow.compile()


def run_master_agent_chat(query: str, history: List[dict], user_id: Optional[str]) -> Dict:
    if not user_id:
        return {
            "response": "Please sign in again. Your user session is missing.",
            "success": False,
            "delegated_to": None,
            "refreshCalendar": False,
            "refreshTasks": False,
        }

    try:
        semantic_context = memory_service.build_context_for_query(user_id, query)
        graph = _build_master_graph()

        initial_state: MasterAgentState = {
            "query": query,
            "history": history,
            "user_id": user_id,
            "semantic_context": semantic_context,
            "route": "general",
            "response": "",
            "success": True,
            "delegated_to": None,
            "refreshCalendar": False,
            "refreshTasks": False,
        }

        result = graph.invoke(initial_state)

        return {
            "response": str(result.get("response") or "Done."),
            "success": bool(result.get("success", True)),
            "delegated_to": result.get("delegated_to"),
            "refreshCalendar": bool(result.get("refreshCalendar", False)),
            "refreshTasks": bool(result.get("refreshTasks", False)),
        }
    except Exception as exc:
        return {
            "response": f"Error running master agent: {exc}",
            "success": False,
            "delegated_to": None,
            "refreshCalendar": False,
            "refreshTasks": False,
        }
