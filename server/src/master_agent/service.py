"""Master agent public facade (NUMA-106 P3, PLAN 16.3).

This file is now a thin re-export surface. The implementation lives in cohesive
sibling modules so existing callers (``from ..master_agent.service import X``)
are unaffected:

  state             - LangGraph state TypedDicts
  common            - dependency loading, LLM access, message/datetime parsing
  day_planner       - plan-my-day context fetch + slot allocation + synthesis
  subagents.task_agent - task sub-agent toolset + graph + run entrypoint
  orchestrator      - delegation toolset, master graph, chat entrypoint
"""
from .common import (
    _format_local_time,
    _get_llm,
    _history_to_messages,
    _is_llm_configured,
    _parse_due_datetime,
    _require_master_dependencies,
)
from .day_planner import (
    _allocate_blocks,
    _fetch_day_planning_context,
    _free_slots_for_day,
    _is_plan_my_day_query,
    _run_day_planner,
)
from .orchestrator import (
    MASTER_AGENT_SYSTEM_PROMPT,
    _answer_general,
    _build_master_graph,
    _master_toolset,
    run_master_agent_chat,
)
from .state import MasterAgentState, MasterToolState, TaskAgentState
from .subagents.task_agent import (
    TASK_SUBAGENT_SYSTEM_PROMPT,
    _build_task_subagent_graph,
    _run_task_subagent,
    _task_toolset,
)

__all__ = [
    # state
    "TaskAgentState", "MasterAgentState", "MasterToolState",
    # common
    "_require_master_dependencies", "_get_llm", "_is_llm_configured",
    "_history_to_messages", "_parse_due_datetime", "_format_local_time",
    # day_planner
    "_is_plan_my_day_query", "_fetch_day_planning_context", "_free_slots_for_day",
    "_allocate_blocks", "_run_day_planner",
    # subagents.task_agent
    "TASK_SUBAGENT_SYSTEM_PROMPT", "_task_toolset", "_build_task_subagent_graph",
    "_run_task_subagent",
    # orchestrator
    "MASTER_AGENT_SYSTEM_PROMPT", "_master_toolset", "_answer_general",
    "_build_master_graph", "run_master_agent_chat",
]
