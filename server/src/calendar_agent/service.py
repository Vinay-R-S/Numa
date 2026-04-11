import operator
import os
import importlib
from datetime import datetime, timedelta
from functools import lru_cache
from typing import Annotated, List, Optional, Sequence, TypedDict

from ..calendar import service as calendar_service
from ..memory import memory_service
from ..memory.service import search_calendar_events as _qdrant_search
from ..tasks import service as task_service


SYSTEM_PROMPT = (
    "You are Numa, a smart calendar assistant with access to the user's Google Calendar data.\n"
    "You receive relevant calendar events as context in the system message — use them to answer"
    " questions directly and accurately.\n"
    "Only call tools when you need to CREATE, EDIT, or DELETE events, search for something not"
    " in the provided context, or add an event to the Task list.\n"
    "If required fields are missing, ask a short clarification question.\n"
    "Never invent event IDs or datetimes."
)


class AgentState(TypedDict):
    messages: Annotated[Sequence[object], operator.add]
    user_query: str
    rag_context: str


def _require_agent_dependencies():
    try:
        messages_module = importlib.import_module("langchain_core.messages")
        tools_module = importlib.import_module("langchain_core.tools")
        groq_module = importlib.import_module("langchain_groq")
        graph_module = importlib.import_module("langgraph.graph")

        AIMessage = getattr(messages_module, "AIMessage")
        HumanMessage = getattr(messages_module, "HumanMessage")
        SystemMessage = getattr(messages_module, "SystemMessage")
        ToolMessage = getattr(messages_module, "ToolMessage")
        tool = getattr(tools_module, "tool")
        ChatGroq = getattr(groq_module, "ChatGroq")
        END = getattr(graph_module, "END")
        StateGraph = getattr(graph_module, "StateGraph")
    except ImportError as exc:
        raise RuntimeError(
            "Agent dependencies are missing. Install langchain, langgraph, langchain-core, and langchain-groq."
        ) from exc

    return {
        "AIMessage": AIMessage,
        "HumanMessage": HumanMessage,
        "SystemMessage": SystemMessage,
        "ToolMessage": ToolMessage,
        "tool": tool,
        "ChatGroq": ChatGroq,
        "StateGraph": StateGraph,
        "END": END,
    }

def _resolve_groq_model(model_override: Optional[str]) -> str:
    default_model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile").strip()
    if not model_override:
        return default_model

    selected = model_override.strip().lower()
    aliases = {
        "70b": "llama-3.3-70b-versatile",
        "8b": "llama-3.1-8b-instant",
        "llama-3.3-70b-versatile": "llama-3.3-70b-versatile",
        "llama-3.1-8b-instant": "llama-3.1-8b-instant",
    }

    return aliases.get(selected, default_model)


def _get_llm(chat_groq_cls, model_override: Optional[str] = None):
    api_key = os.getenv("GROQ_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("GROQ_API_KEY is not configured")

    model = _resolve_groq_model(model_override)
    temperature = float(os.getenv("GROQ_TEMPERATURE", "0.2"))
    return chat_groq_cls(model=model, temperature=temperature, api_key=api_key)


def _is_groq_configured() -> bool:
    api_key = os.getenv("GROQ_API_KEY", "").strip()
    if not api_key:
        return False

    lower = api_key.lower()
    if lower in {"your_groq_api_key_here", "gsk_your_groq_api_key_here", "your_groq_key"}:
        return False

    return True


def _build_rag_context(user_id: str, query: str) -> str:
    """
    Pull the top-6 semantically relevant calendar events from Qdrant and format
    them as a compact context block to inject into the system prompt.
    Returns an empty string if Qdrant is unavailable or no results found.
    """
    if not user_id:
        return ""
    try:
        hits = _qdrant_search(user_id, query, limit=6)
        if not hits:
            return ""

        lines = ["\n[Your Calendar — Relevant Events from this month]"]
        for evt in hits:
            title = evt.get("title") or "(No title)"
            start = evt.get("start_at") or ""
            end   = evt.get("end_at") or ""
            desc  = evt.get("description") or ""

            # Format: "• Title | Start → End | Description"
            try:
                start_dt = datetime.fromisoformat(start)
                end_dt   = datetime.fromisoformat(end)
                time_str = (
                    f"{start_dt.strftime('%b %d, %I:%M %p')} → {end_dt.strftime('%I:%M %p')}"
                )
            except Exception:
                time_str = start

            entry = f"• {title} | {time_str}"
            if desc:
                entry += f" | {desc[:80]}"
            lines.append(entry)
        return "\n".join(lines)
    except Exception:
        return ""


def _toolset(tool_decorator, user_id: str | None):
    @tool_decorator
    def schedule_event(
        title: str,
        datetime_str: str,
        duration_minutes: int = 60,
        attendees: list = None,
        create_meet: bool = False,
    ) -> str:
        """Create a new calendar event with optional attendees and meet link."""
        try:
            result = calendar_service.create_calendar_event(
                title=title,
                datetime_str=datetime_str,
                duration_minutes=duration_minutes,
                attendees=attendees,
                create_meet=create_meet,
                user_id=user_id,
            )
            if result.get("status") == "duplicate_prevented":
                return (
                    "Duplicate event detected and not created. "
                    f"Title: {result['summary']} Start: {result['start']}"
                )
            return (
                "Event created successfully. "
                f"Title: {result['summary']} Start: {result['start']}"
            )
        except Exception as exc:
            return f"Error creating event: {exc}"

    @tool_decorator
    def get_events(days: int = 8) -> str:
        """List events in a time window: past 7 days and future N days (excludes holidays/festivals)."""
        try:
            events = calendar_service.list_events_in_window(
                lookback_days=7,
                lookahead_days=days,
                user_id=user_id,
            )
            if not events:
                return "No events found in the time window."
            lines = [f"Events in window ({len(events)}):"]
            for event in events:
                lines.append(
                    f"- {event['summary']} at {event['start']} [{event.get('calendar', 'Primary')}]"
                )
            return "\n".join(lines)
        except Exception as exc:
            return f"Error fetching events: {exc}"

    @tool_decorator
    def get_events_on_date(date: str) -> str:
        """List all events scheduled on a specific date (YYYY-MM-DD)."""
        try:
            events = calendar_service.get_events_on_date(date, user_id=user_id)
            if not events:
                return f"No events found on {date}."
            lines = [f"Events on {date}:"]
            for event in events:
                lines.append(
                    f"- {event['summary']} at {event['start']} [{event.get('calendar', 'Primary')}]"
                )
            return "\n".join(lines)
        except Exception as exc:
            return f"Error fetching events for {date}: {exc}"

    @tool_decorator
    def delete_event(event_id: str) -> str:
        """Delete a calendar event by id."""
        try:
            result = calendar_service.delete_calendar_event(event_id, user_id=user_id)
            return f"Event deleted successfully. ID: {result['deleted_event_id']}"
        except Exception as exc:
            return f"Error deleting event: {exc}"

    @tool_decorator
    def delete_by_description(query: str) -> str:
        """Delete an event by matching text in its description or summary."""
        try:
            result = calendar_service.delete_event_by_description(query, user_id=user_id)
            status = result.get("status")
            if status == "not_found":
                return result["message"]
            if status == "deleted":
                return (
                    "Event deleted successfully. "
                    f"Title: {result['deleted_summary']} Was at: {result['deleted_start']}"
                )
            if status == "multiple_matches":
                lines = [result["message"]]
                for idx, match in enumerate(result["matches"], start=1):
                    lines.append(f"{idx}. {match['summary']} at {match['start']}")
                return "\n".join(lines)
            return "Unexpected delete result"
        except Exception as exc:
            return f"Error deleting event: {exc}"

    @tool_decorator
    def modify_event(query: str, new_datetime_str: str) -> str:
        """Reschedule an event matched by description text to a new datetime."""
        try:
            result = calendar_service.modify_event_by_description(query, new_datetime_str, user_id=user_id)
            status = result.get("status")
            if status == "not_found":
                return result["message"]
            if status == "multiple_matches":
                lines = [result["message"]]
                for idx, match in enumerate(result["matches"], start=1):
                    lines.append(f"{idx}. {match['summary']} at {match['start']}")
                return "\n".join(lines)
            if status == "modified":
                return (
                    "Event rescheduled successfully. "
                    f"Title: {result['summary']} New time: {result['new_start']}"
                )
            return "Unexpected modify result"
        except Exception as exc:
            return f"Error modifying event: {exc}"

    @tool_decorator
    def find_free_slots(date: str, duration_minutes: int = 30) -> str:
        """Find available free time slots for a date and minimum duration."""
        try:
            result = calendar_service.find_free_slots(date, duration_minutes, user_id=user_id)
            if not result["free_slots"]:
                return f"No free slots of {duration_minutes}+ minutes found on {result['date']}."
            lines = [f"Free slots on {result['date']} (>= {duration_minutes} min):"]
            for slot in result["free_slots"]:
                lines.append(
                    f"- {slot['start']} to {slot['end']} ({slot['duration_minutes']} min)"
                )
            return "\n".join(lines)
        except Exception as exc:
            return f"Error finding free slots: {exc}"

    @tool_decorator
    def search_calendar_rag(query: str) -> str:
        """
        Search the user's calendar events semantically using RAG (Qdrant vector search).
        Use this to find events by topic, type, or description when the system context
        does not already contain the answer. Returns the top matching events.
        """
        if not user_id:
            return "User not authenticated — cannot search calendar."
        try:
            hits = _qdrant_search(user_id, query, limit=8)
            if not hits:
                return "No matching calendar events found in the RAG index."
            lines = [f"Calendar RAG results for '{query}':"]
            for evt in hits:
                title = evt.get("title") or "(No title)"
                start = evt.get("start_at") or ""
                end   = evt.get("end_at") or ""
                try:
                    start_dt = datetime.fromisoformat(start)
                    end_dt   = datetime.fromisoformat(end)
                    time_str = (
                        f"{start_dt.strftime('%b %d, %I:%M %p')} → {end_dt.strftime('%I:%M %p')}"
                    )
                except Exception:
                    time_str = start
                lines.append(f"- {title} | {time_str}")
            return "\n".join(lines)
        except Exception as exc:
            return f"Error searching calendar RAG: {exc}"

    @tool_decorator
    def add_today_as_task(event_title: str, event_start_time: str, description: str = "") -> str:
        """
        Add a specific calendar event to today's Task list.
        Use this when the user explicitly asks to add an event as a task,
        or when an event needs to appear in today's task list.
        event_start_time should be in ISO format (YYYY-MM-DDTHH:MM:SS).
        """
        if not user_id:
            return "User not authenticated — cannot add task."
        try:
            now = datetime.now(calendar_service.TIMEZONE)
            today_str = now.date().isoformat()

            # Parse start time
            try:
                start_dt = datetime.fromisoformat(event_start_time)
                reminder_at = start_dt - timedelta(minutes=15)
            except Exception:
                start_dt = now
                reminder_at = None

            from ..calendar.service import get_all_connected_user_ids  # noqa: F401
            external_ref = f"gcal:manual:{user_id}:{event_title.strip().lower().replace(' ', '-')}"

            task_service.upsert_calendar_event_task(
                user_id=user_id,
                external_ref=external_ref,
                title=event_title.strip() or "(No title)",
                description=description.strip() or None,
                due_date=start_dt,
                reminder_at=reminder_at,
            )
            return f"Added '{event_title}' to your task list for today ({today_str})."
        except Exception as exc:
            return f"Error adding task: {exc}"

    return [
        schedule_event,
        get_events,
        get_events_on_date,
        delete_event,
        delete_by_description,
        modify_event,
        find_free_slots,
        search_calendar_rag,
        add_today_as_task,
    ]


@lru_cache(maxsize=64)
def _build_agent_graph(user_id: str | None, model_override: Optional[str] = None):
    deps = _require_agent_dependencies()

    AIMessage = deps["AIMessage"]
    SystemMessage = deps["SystemMessage"]
    ToolMessage = deps["ToolMessage"]
    StateGraph = deps["StateGraph"]
    END = deps["END"]

    tools = _toolset(deps["tool"], user_id)
    tool_map = {tool.name: tool for tool in tools}

    required_args = {
        "schedule_event": {"title", "datetime_str"},
        "delete_event": {"event_id"},
        "delete_by_description": {"query"},
        "modify_event": {"query", "new_datetime_str"},
        "find_free_slots": {"date"},
        "search_calendar_rag": {"query"},
        "add_today_as_task": {"event_title", "event_start_time"},
    }

    def validate_tool_call(tool_name: str, args: dict) -> str | None:
        required = required_args.get(tool_name)
        if not required:
            return None
        missing = [key for key in required if key not in args]
        if missing:
            return f"Missing required arguments for {tool_name}: {missing}"
        return None

    def call_model(state: AgentState) -> AgentState:
        llm = _get_llm(deps["ChatGroq"], model_override=model_override)
        llm_with_tools = llm.bind_tools(tools)

        now = datetime.now(calendar_service.TIMEZONE)
        runtime_context = (
            "\nRuntime context:\n"
            f"Current date: {now.strftime('%Y-%m-%d')}\n"
            f"Current time: {now.strftime('%H:%M')} {calendar_service.TIMEZONE_NAME}\n"
            f"Today: {now.strftime('%Y-%m-%d')}\n"
            f"Tomorrow: {(now + timedelta(days=1)).strftime('%Y-%m-%d')}\n"
        )

        # RAG context is injected per-turn from the state's stored rag_context
        rag_context = state.get("rag_context", "")

        full_system = SYSTEM_PROMPT + runtime_context
        if rag_context:
            full_system += rag_context

        full_messages = [SystemMessage(content=full_system)] + list(state["messages"])
        response = llm_with_tools.invoke(full_messages)
        return {
            "messages": [response],
            "user_query": state["user_query"],
        }

    def call_tools(state: AgentState) -> AgentState:
        last_message = state["messages"][-1]
        tool_messages = []

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
                except Exception as exc:
                    result = f"Error executing {tool_name}: {exc}"

            tool_messages.append(ToolMessage(content=str(result), tool_call_id=tool_id))

        return {
            "messages": tool_messages,
            "user_query": state["user_query"],
        }

    def should_continue(state: AgentState):
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

    workflow = StateGraph(AgentState)
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


def run_agent_chat(
    query: str,
    history: List[dict],
    user_id: str | None = None,
    model: Optional[str] = None,
):
    if not _is_groq_configured():
        return {
            "response": (
                "Calendar sub-agent is unavailable right now because GROQ_API_KEY is not configured on the backend. "
                "Add GROQ_API_KEY in server/.env and restart the backend server."
            ),
            "success": True,
            "refreshCalendar": False,
        }

    try:
        deps = _require_agent_dependencies()
        HumanMessage = deps["HumanMessage"]
        AIMessage = deps["AIMessage"]

        graph, AIMessageType = _build_agent_graph(user_id, model)

        # ── RAG context: pull relevant calendar events from Qdrant ──────────
        rag_context = ""
        if user_id:
            rag_context = _build_rag_context(user_id, query)

        # ── Conversational memory context ────────────────────────────────────
        contextual_query = query
        if user_id:
            memory_context = memory_service.build_context_for_query(user_id, query)
            if memory_context:
                contextual_query = (
                    f"{query}\n\n"
                    "Relevant semantic memory (same user, similar prior turns):\n"
                    f"{memory_context}\n"
                    "Use this context only if it helps answer accurately."
                )

        history_messages = []
        for message in history:
            content = (message.get("content") or "").strip()
            if not content:
                continue

            role = (message.get("role") or "").lower()
            if role == "user":
                history_messages.append(HumanMessage(content=content))
            elif role in ("assistant", "ai"):
                history_messages.append(AIMessage(content=content))

        initial_state = {
            "messages": history_messages + [HumanMessage(content=contextual_query)],
            "user_query": query,
            "rag_context": rag_context,
        }
        result = graph.invoke(initial_state)

        messages = result.get("messages", [])
        if not messages:
            raise RuntimeError("Agent did not produce any response")

        final_message = messages[-1]
        response_text = getattr(final_message, "content", str(final_message))
        if isinstance(final_message, AIMessageType) and isinstance(response_text, list):
            response_text = "\n".join(str(part) for part in response_text)

        mutation_keywords = (
            "schedule",
            "create",
            "add",
            "delete",
            "remove",
            "cancel",
            "reschedule",
            "move",
            "modify",
            "update",
            "undo",
        )
        query_has_mutation = any(word in query.lower() for word in mutation_keywords)
        response_confirms_mutation = any(
            phrase in str(response_text).lower()
            for phrase in (
                "created",
                "deleted",
                "rescheduled",
                "modified",
                "updated",
            )
        )

        if user_id and str(response_text).strip():
            memory_service.store_turn(user_id, query, str(response_text))

        return {
            "response": str(response_text),
            "success": True,
            "refreshCalendar": query_has_mutation or response_confirms_mutation,
        }
    except Exception as exc:
        return {
            "response": f"Error running agent: {exc}",
            "success": False,
            "refreshCalendar": False,
        }
