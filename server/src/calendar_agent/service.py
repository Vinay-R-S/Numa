import operator
import os
import importlib
from datetime import datetime, timedelta
from functools import lru_cache
from typing import Annotated, List, Sequence, TypedDict

from ..calendar import service as calendar_service
from ..memory import memory_service


SYSTEM_PROMPT = (
    "You are Numa, a conversational calendar assistant."
    " You can only act through the available calendar tools."
    " If required fields are missing, ask a short clarification question."
    " Never invent event ids or datetimes."
)


class AgentState(TypedDict):
    messages: Annotated[Sequence[object], operator.add]
    user_query: str


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


def _get_llm(chat_groq_cls):
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY is not configured")

    model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    temperature = float(os.getenv("GROQ_TEMPERATURE", "0.2"))
    return chat_groq_cls(model=model, temperature=temperature, api_key=api_key)


def _toolset(tool_decorator, user_id: str | None):
    @tool_decorator
    def schedule_event(
        title: str,
        datetime_str: str,
        duration_minutes: int = 60,
        attendees: list = None,
        create_meet: bool = False,
    ) -> str:
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
    def get_events(days: int = 1) -> str:
        try:
            events = calendar_service.list_upcoming_events(days, user_id=user_id)
            if not events:
                return "No upcoming events found."
            lines = [f"Upcoming events ({len(events)}):"]
            for event in events:
                lines.append(
                    f"- {event['summary']} at {event['start']} [{event.get('calendar', 'Primary')}]"
                )
            return "\n".join(lines)
        except Exception as exc:
            return f"Error fetching events: {exc}"

    @tool_decorator
    def get_events_on_date(date: str) -> str:
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
        try:
            result = calendar_service.delete_calendar_event(event_id, user_id=user_id)
            return f"Event deleted successfully. ID: {result['deleted_event_id']}"
        except Exception as exc:
            return f"Error deleting event: {exc}"

    @tool_decorator
    def delete_by_description(query: str) -> str:
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

    return [
        schedule_event,
        get_events,
        get_events_on_date,
        delete_event,
        delete_by_description,
        modify_event,
        find_free_slots,
    ]


@lru_cache(maxsize=64)
def _build_agent_graph(user_id: str | None):
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
        llm = _get_llm(deps["ChatGroq"])
        llm_with_tools = llm.bind_tools(tools)

        now = datetime.now(calendar_service.TIMEZONE)
        runtime_context = (
            "\nRuntime context:\n"
            f"Current date: {now.strftime('%Y-%m-%d')}\n"
            f"Current time: {now.strftime('%H:%M')} {calendar_service.TIMEZONE_NAME}\n"
            f"Today: {now.strftime('%Y-%m-%d')}\n"
            f"Tomorrow: {(now + timedelta(days=1)).strftime('%Y-%m-%d')}\n"
        )

        full_messages = [SystemMessage(content=SYSTEM_PROMPT + runtime_context)] + list(state["messages"])
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


def run_agent_chat(query: str, history: List[dict], user_id: str | None = None):
    try:
        deps = _require_agent_dependencies()
        HumanMessage = deps["HumanMessage"]
        AIMessage = deps["AIMessage"]

        graph, AIMessageType = _build_agent_graph(user_id)

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
