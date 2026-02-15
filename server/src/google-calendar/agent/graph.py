"""
LangGraph Agent
Binds LangChain tools to Gemini LLM with comprehensive debug logging.
Handles tool-calling decisions, execution, and error recovery.
"""

from typing import Literal
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, SystemMessage
from agent.state import AgentState
from agent.llm import get_llm
from agent.tools import TOOLS

# ---------------------------------------------------------------
# System prompt: guides Gemini on when/how to use tools.
# Explicit instructions reduce hallucinated tool calls.
# ---------------------------------------------------------------
SYSTEM_PROMPT = (
    "You are a tool-driven AI assistant.\n"
    "Your capabilities exist ONLY through the provided tools.\n\n"

    "CORE PRINCIPLE:\n"
    "You do not have calendar knowledge or email abilities yourself.\n"
    "All real actions MUST occur via tools.\n\n"

    "MANDATORY TOOL PROTOCOL:\n"
    "- Tools are strict APIs, not suggestions.\n"
    "- Their function signatures are law.\n"
    "- Any deviation is a failure.\n\n"

    "ABSOLUTE RULES (NON NEGOTIABLE):\n"
    "1. Never invent tool parameters.\n"
    "2. Never rename arguments.\n"
    "3. Never guess missing values.\n"
    "4. Never call tools with partial required arguments.\n"
    "5. Never assume default values unless explicitly defined.\n"
    "6. Never generate placeholder values.\n\n"

    "ARGUMENT SAFETY RULES:\n"
    "- Use ONLY parameters defined by the tool.\n"
    "- Ignore natural language variable names.\n"
    "- Map user intent to tool parameters exactly.\n"
    "- If a parameter is not defined by the tool, it does not exist.\n\n"

    "WHEN TO CALL TOOLS:\n"
    "- Call a tool ONLY if the user intent clearly matches it.\n"
    "- Call a tool ONLY if ALL required arguments are known.\n"
    "- Otherwise ask a clarification question.\n\n"

    "SCHEDULING RULES:\n"
    "- `schedule_event` REQUIRES title and datetime_str.\n"
    "- When the user uses relative dates, resolve them using the CURRENT DATE provided below:\n"
    "  • 'today' → current date (from runtime context)\n"
    "  • 'tomorrow' or 'tmr' → current date + 1 day\n"
    "- The model MUST compute the date using runtime context, not probabilistic reasoning.\n"
    "- Never produce any other date. Never skip days. Never add multiple days. Never guess.\n"
    "- If time is vague (e.g. 'evening', 'morning', 'later') → ask the user for a specific time.\n"
    "- NEVER invent or fabricate ISO datetime values.\n\n"

    "MEETING RULES:\n"
    "When the user's intent involves a meeting, call, sync, discussion, or Google Meet:\n"
    "- ALWAYS use `schedule_event` — it auto-generates a Google Meet link for every event.\n"
    "- If attendee emails are mentioned, pass them as the `attendees` list.\n"
    "- NEVER create a plain calendar event without a Meet link for meeting intent.\n"
    "- Extract participant emails from the user's message when available.\n\n"

    "EVENT QUERY RULES:\n"
    "- ALWAYS use get_events for schedule related questions.\n"
    "- NEVER answer schedule questions from memory.\n"
    "- Use ONLY supported parameters.\n\n"

    "DELETION RULES:\n"
    "- If the user asks to delete/remove/cancel an event WITHOUT providing an event_id:\n"
    "  → MUST call `delete_by_description` with the user's phrase as `query`.\n"
    "  → NEVER ask the user for an event ID directly.\n"
    "  → NEVER guess or fabricate event IDs.\n"
    "  → If the tool returns multiple matches, present them and ask the user to pick one.\n"
    "  → Examples: 'cancel my gym', 'remove dentist appointment', 'delete meeting with Rahul'.\n"
    "- If the user provides an explicit event_id, use `delete_event` instead.\n\n"

    "RESCHEDULING RULES:\n"
    "When the user expresses intent to move, reschedule, change time, or postpone an event:\n"
    "- MUST use `modify_event` tool with the event description as `query` and new time as `new_datetime_str`.\n"
    "- NEVER create a new event for rescheduling intent.\n"
    "- NEVER delete + recreate — always modify in place.\n"
    "- NEVER duplicate events.\n"
    "- If multiple matches are found, present the list and ask the user to clarify.\n\n"

    "AVAILABILITY RULES:\n"
    "When the user asks about availability, free time, open slots, or when they can schedule:\n"
    "- ALWAYS call `find_free_slots` with the target date and desired duration.\n"
    "- NEVER answer availability questions from memory or reasoning.\n"
    "- Present the returned slots clearly to the user.\n\n"

    "FAIL SAFE BEHAVIOR:\n"
    "If ANY uncertainty exists about tool usage or parameters:\n"
    "→ Do NOT call tools\n"
    "→ Ask the user a question instead\n\n"

    "TOOL ERROR HANDLING:\n"
    "If a tool returns an error:\n"
    "- The model MUST NOT retry the same tool call with identical arguments.\n"
    "- The model MUST analyze the error message.\n"
    "- The model MUST correct the arguments before the next call.\n"
    "- If correction is not possible → respond to the user with a clear explanation.\n"
    "- Under no circumstance may the model repeat identical failing tool calls.\n\n"

    "Your priority order:\n"
    "Correctness > Tool Safety > Helpfulness > Brevity"
)


def call_model(state: AgentState) -> AgentState:
    """
    Invoke Gemini LLM with tools explicitly bound.
    
    Logs user input, raw LLM output, and tool-call detection.
    
    Args:
        state: Current agent state with message history
    
    Returns:
        AgentState: Updated state with LLM response
    """
    messages = state['messages']
    
    # ── Debug: user input ──────────────────────────────────────
    print("\n" + "=" * 60)
    print("🔵 USER INPUT:")
    print("=" * 60)
    for msg in messages:
        if isinstance(msg, HumanMessage):
            print(f"  {msg.content}")
        elif isinstance(msg, ToolMessage):
            print(f"  [Tool Result] {msg.content[:120]}...")
    
    # ── Bind tools to LLM ─────────────────────────────────────
    llm = get_llm()
    llm_with_tools = llm.bind_tools(TOOLS)
    
    # Inject current IST date into system prompt for deterministic date resolution
    from datetime import datetime as _dt, timedelta as _td
    import pytz as _pytz
    _ist = _pytz.timezone('Asia/Kolkata')
    _now = _dt.now(_ist)
    _date_context = (
        f"\n\nRUNTIME CONTEXT (source of truth for dates):\n"
        f"Current date: {_now.strftime('%Y-%m-%d')}\n"
        f"Current time: {_now.strftime('%H:%M')} IST\n"
        f"Today = {_now.strftime('%Y-%m-%d')}\n"
        f"Tomorrow = {(_now + _td(days=1)).strftime('%Y-%m-%d')}\n"
    )
    full_messages = [SystemMessage(content=SYSTEM_PROMPT + _date_context)] + list(messages)
    
    # Invoke LLM
    response = llm_with_tools.invoke(full_messages)
    
    # ── Debug: raw LLM output ─────────────────────────────────
    print("\n" + "=" * 60)
    print("🤖 LLM RAW OUTPUT:")
    print("=" * 60)
    print(f"  Content : {response.content or '(empty – tool call only)'}")
    print(f"  Type    : {type(response).__name__}")
    
    # ── Debug: tool-call detection ────────────────────────────
    has_tool_calls = (
        hasattr(response, 'tool_calls')
        and response.tool_calls
        and len(response.tool_calls) > 0
    )
    print(f"\n  🔧 Tool Call Triggered: {has_tool_calls}")
    
    if has_tool_calls:
        for i, tc in enumerate(response.tool_calls, 1):
            print(f"     Call {i}: {tc.get('name')}  →  args={tc.get('args', {})}")
    else:
        print("     → Direct text response (no tool invoked)")
    
    return {
        "messages": [response],
        "user_query": state['user_query']
    }


def call_tools(state: AgentState) -> AgentState:
    """
    Execute each tool the LLM requested.
    
    Validates tool name, invokes with args, and captures errors
    so the agent can report failures cleanly instead of crashing.
    
    Args:
        state: Current agent state
    
    Returns:
        AgentState: Updated state with ToolMessages
    """
    last_message = state['messages'][-1]
    tool_messages = []
    
    # Build a name→tool lookup for O(1) access
    tool_map = {t.name: t for t in TOOLS}
    
    print("\n" + "=" * 60)
    print("⚙️  EXECUTING TOOLS:")
    print("=" * 60)
    
    for tc in last_message.tool_calls:
        tool_name = tc.get('name')
        tool_args = tc.get('args', {})
        tool_id   = tc.get('id')
        
        print(f"\n  → Tool  : {tool_name}")
        print(f"    Args  : {tool_args}")
        
        # Pre-validate required arguments before execution
        validation_error = validate_tool_call(tc)
        if validation_error:
            result = validation_error
            print(f"    ❌ {result}")
        elif tool_name not in tool_map:
            # Guard against hallucinated tool names
            result = f"Error: Unknown tool '{tool_name}'. Available tools: {list(tool_map.keys())}"
            print(f"    ❌ {result}")
        else:
            try:
                result = tool_map[tool_name].invoke(tool_args)
                print(f"    ✅ Result:\n       {result}")
            except Exception as e:
                result = f"Error executing {tool_name}: {str(e)}"
                print(f"    ❌ {result}")
        
        tool_messages.append(
            ToolMessage(content=str(result), tool_call_id=tool_id)
        )
    
    return {
        "messages": tool_messages,
        "user_query": state['user_query']
    }


# ── Required argument definitions for pre-call validation ─────
REQUIRED_ARGS = {
    "schedule_event": {"title", "datetime_str"},
    "delete_event": {"event_id"},
    "delete_by_description": {"query"},
    "modify_event": {"query", "new_datetime_str"},
    "find_free_slots": {"date"},
}


def validate_tool_call(tool_call):
    """
    Validate a tool call has all required arguments before execution.
    
    Returns:
        str or None: Error message if validation fails, None if valid
    """
    tool_name = tool_call.get('name')
    args = tool_call.get('args', {})
    
    required = REQUIRED_ARGS.get(tool_name)
    if required is None:
        return None  # No strict validation defined for this tool
    
    missing = [arg for arg in required if arg not in args]
    if missing:
        return f"Error: Missing required arguments for '{tool_name}': {missing}"
    
    return None


def should_continue(state: AgentState) -> Literal["call_tools", "end"]:
    """
    Route based on whether the LLM produced tool_calls.
    Includes a max-iterations guard to prevent infinite retry loops.
    """
    last = state['messages'][-1]
    
    # Count how many tool-call cycles have occurred
    tool_call_rounds = sum(
        1 for m in state['messages']
        if hasattr(m, 'tool_calls') and m.tool_calls
    )
    
    MAX_TOOL_ROUNDS = 3
    
    if tool_call_rounds >= MAX_TOOL_ROUNDS:
        print(f"\n⛔ Max tool-call rounds ({MAX_TOOL_ROUNDS}) reached — stopping loop.")
        return "end"
    
    if hasattr(last, 'tool_calls') and last.tool_calls:
        return "call_tools"
    return "end"


def build_agent_graph():
    """
    Build and compile the LangGraph state machine.
    
    Flow:
      START → call_model ─┬─ tool_calls? → call_tools → call_model ─┐
                           └─ no ──────────────────────────── END ◄──┘
    """
    workflow = StateGraph(AgentState)
    
    workflow.add_node("call_model", call_model)
    workflow.add_node("call_tools", call_tools)
    
    workflow.set_entry_point("call_model")
    
    workflow.add_conditional_edges(
        "call_model",
        should_continue,
        {"call_tools": "call_tools", "end": END}
    )
    
    # After tool execution, return to model so it can summarise results
    workflow.add_edge("call_tools", "call_model")
    
    return workflow.compile()


# Compile once at import time
agent_graph = build_agent_graph()
