"""
Health Sub-Agent Service
========================
LangGraph agentic loop for health-related queries.

Tools:
  get_todays_health     - fetch today's health snapshot from Supabase
  get_weekly_health     - fetch last 7 days of health data
  sync_health_data      - trigger a fresh sync from Google Fit / Strava
  get_health_insights   - generate insights from current data

Entry point:
  run_health_agent_chat(query, history, user_id, model=None) -> Dict
"""
from __future__ import annotations

import importlib
import json
import logging
import os
from datetime import date, datetime, timedelta, timezone
from typing import Annotated, Dict, List, Optional, Sequence, TypedDict

import operator

log = logging.getLogger(__name__)

HEALTH_AGENT_SYSTEM_PROMPT = (
    "You are NUMA Health sub-agent. You help users understand their health and fitness data "
    "from Google Fit and Strava. You can fetch today's metrics, show weekly trends, "
    "sync fresh data, provide personalized health insights, and recommend diet plans. "
    "Always use tools to fetch real data - never fabricate health numbers. "
    "If Google Fit is not configured, guide users to set it up. "
    "Keep responses encouraging, concise, and health-focused. "
    "When providing diet or food recommendations, ALWAYS include this disclaimer at the start: "
    "'DISCLAIMER: These are general suggestions based on your activity data and are NOT medical advice. "
    "Consult a healthcare professional or registered dietitian before making dietary changes.' "
    "You can also recommend yoga poses from the Mental Peace section based on user health data."
)

DIET_DISCLAIMER = (
    "DISCLAIMER: These are general suggestions based on your activity data and are NOT medical advice.\n"
    "Consult a healthcare professional or registered dietitian before making dietary changes."
)


def _is_diet_query(query: str) -> bool:
    q = (query or "").lower()
    return any(
        term in q
        for term in (
            "diet",
            "meal",
            "nutrition",
            "food",
            "eat",
            "breakfast",
            "lunch",
            "dinner",
            "protein",
            "calorie intake",
        )
    )


def _valid_number(value) -> Optional[float]:
    if value is None:
        return None
    try:
        n = float(value)
    except (TypeError, ValueError):
        return None
    return n if n > 0 else None


def _fmt_metric(value: float, unit: str) -> str:
    if unit == "km":
        return f"{value:.1f} km"
    if unit == "hours":
        return f"{value:.1f} hours"
    return f"{int(round(value)):,} {unit}"


def _build_diet_recommendation(user_id: str) -> str:
    from .router import get_health_snapshots

    snapshots = get_health_snapshots(user_id, days=8)
    today = date.today()
    today_snaps = [s for s in snapshots if s.get("snapshot_date") == today]

    def best_metric(key: str) -> Optional[float]:
        values = [_valid_number(s.get(key)) for s in today_snaps]
        values = [v for v in values if v is not None]
        return max(values) if values else None

    steps = best_metric("steps")
    active = best_metric("active_minutes")
    calories = best_metric("calories")
    distance = best_metric("distance_km")
    sleep = best_metric("sleep_hours")

    available = {
        "steps": steps,
        "active_minutes": active,
        "calories": calories,
        "distance_km": distance,
        "sleep_hours": sleep,
    }
    used_metrics = {k: v for k, v in available.items() if v is not None}

    activity_signals = []
    if steps is not None:
        if steps >= 10000:
            activity_signals.append("high")
        elif steps >= 5000:
            activity_signals.append("moderate")
        else:
            activity_signals.append("low")
    if active is not None:
        if active >= 60:
            activity_signals.append("high")
        elif active >= 30:
            activity_signals.append("moderate")
        else:
            activity_signals.append("low")
    if distance is not None:
        if distance >= 8:
            activity_signals.append("high")
        elif distance >= 3:
            activity_signals.append("moderate")
        else:
            activity_signals.append("low")

    high_count = activity_signals.count("high")
    moderate_count = activity_signals.count("moderate")
    if high_count:
        activity_level = "active"
        plate_focus = "higher complex carbs with lean protein for recovery"
        snack_focus = "a protein-rich snack plus fruit after activity"
    elif moderate_count:
        activity_level = "moderate"
        plate_focus = "balanced carbs, protein, and vegetables"
        snack_focus = "a light protein snack if meals are spaced far apart"
    elif activity_signals:
        activity_level = "light"
        plate_focus = "vegetables, lean protein, and controlled portions of carbs"
        snack_focus = "fruit, yogurt, nuts, or sprouts instead of sugary snacks"
    else:
        activity_level = "unknown"
        plate_focus = "balanced meals with protein, fiber-rich carbs, and vegetables"
        snack_focus = "simple whole-food snacks like fruit, yogurt, or nuts"

    if calories is not None and calories >= 2400:
        energy_note = "Your calorie burn looks high today, so include enough carbs and protein to support recovery."
    elif calories is not None and calories >= 1800:
        energy_note = "Your calorie burn looks moderate, so a balanced intake should fit well."
    elif calories is not None:
        energy_note = "Your logged calorie burn is on the lighter side, so keep meals nutrient-dense without oversized portions."
    else:
        energy_note = None

    lines = [
        DIET_DISCLAIMER,
        "",
        "Diet plan based on available health data:",
    ]

    if used_metrics:
        lines.append("Data considered:")
        if steps is not None:
            lines.append(f"- Steps: {_fmt_metric(steps, 'steps')}")
        if active is not None:
            lines.append(f"- Active minutes: {_fmt_metric(active, 'min')}")
        if calories is not None:
            lines.append(f"- Calories burned: {_fmt_metric(calories, 'kcal')}")
        if distance is not None:
            lines.append(f"- Distance: {_fmt_metric(distance, 'km')}")
        if sleep is not None:
            lines.append(f"- Sleep: {_fmt_metric(sleep, 'hours')}")
    else:
        lines.append("No usable health metrics are available yet, so this is a general balanced plan.")

    lines.extend(
        [
            "",
            f"Activity read: {activity_level.capitalize()}",
            f"Main focus: {plate_focus}.",
        ]
    )
    if energy_note:
        lines.append(energy_note)

    lines.extend(
        [
            "",
            "Suggested meals:",
            "- Breakfast: Oats or whole-grain toast with eggs, paneer, tofu, or Greek yogurt, plus fruit.",
            "- Lunch: Rice, roti, or quinoa with dal, chicken, fish, paneer, tofu, or beans, plus vegetables.",
            "- Snack: " + snack_focus + ".",
            "- Dinner: Lean protein with cooked vegetables and a smaller portion of rice, roti, or potatoes.",
            "- Hydration: Water through the day; add electrolytes only if you had heavy sweating or a long workout.",
        ]
    )

    if sleep is not None and sleep < 6:
        lines.extend(
            [
                "",
                "Sleep-aware adjustment: Since sleep is low, avoid late caffeine and keep dinner lighter. Add magnesium-rich foods like spinach, nuts, seeds, or dal.",
            ]
        )

    if active is not None and active >= 60 or steps is not None and steps >= 10000:
        lines.extend(
            [
                "",
                "Recovery adjustment: Add 20-30g protein after your most active period and include carbs like rice, banana, oats, or potatoes.",
            ]
        )

    return "\n".join(lines)


class HealthAgentState(TypedDict):
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
        raise RuntimeError(f"Health agent dependencies missing: {exc}") from exc


def _get_llm(model_override: Optional[str] = None, user_id: Optional[str] = None):
    from ..llm_factory import get_llm_with_fallback
    return get_llm_with_fallback(
        user_id=user_id,
        agent_name="health",
        priority="normal",
        model=model_override,
    )


def _health_toolset(tool_decorator, user_id: str):
    from .router import (
        get_health_snapshots,
        sync_google_fit_for_user,
        _sync_strava_with_health_all,
        sync_strava_for_user,
    )
    from ..tasks.agent_tools import make_task_tools

    @tool_decorator
    def get_todays_health() -> str:
        """Get today's health data (steps, calories, active minutes, sleep, distance) from stored snapshots.
        Use this when the user asks about their current health, today's progress, or metrics."""
        snapshots = get_health_snapshots(user_id, days=1)
        today_snaps = [s for s in snapshots if s.get("snapshot_date") == date.today()]
        if not today_snaps:
            return "No health data for today yet. Try syncing first with sync_health_data."
        lines = []
        for s in today_snaps:
            src = s.get("source", "unknown")
            lines.append(f"Source: {src}")
            if s.get("steps") is not None:
                lines.append(f"  Steps: {s['steps']:,}")
            if s.get("active_minutes") is not None:
                lines.append(f"  Active Minutes: {s['active_minutes']}")
            if s.get("calories") is not None:
                lines.append(f"  Calories: {s['calories']:,} kcal")
            if s.get("distance_km") is not None:
                lines.append(f"  Distance: {s['distance_km']} km")
            if s.get("sleep_hours") is not None:
                lines.append(f"  Sleep: {s['sleep_hours']} hours")
                stages = s.get("sleep_stages")
                if stages:
                    if isinstance(stages, str):
                        stages = json.loads(stages)
                    lines.append(f"    Deep: {stages.get('deep', 0)}h, Light: {stages.get('light', 0)}h, "
                                 f"REM: {stages.get('rem', 0)}h")
            acts = s.get("activities")
            if acts:
                if isinstance(acts, str):
                    acts = json.loads(acts)
                if isinstance(acts, dict):
                    lines.append(f"  Activities: {', '.join(f'{k} ({v}x)' for k, v in acts.items())}")
        return "\n".join(lines)

    @tool_decorator
    def get_weekly_health() -> str:
        """Get the last 7 days of health data for trend analysis.
        Use this when the user asks about weekly trends, progress over time, or comparisons."""
        snapshots = get_health_snapshots(user_id, source="google_fit", days=8)
        if not snapshots:
            return "No weekly health data available. Try syncing Google Fit data first."
        lines = ["Weekly Health Summary (Google Fit):"]
        for s in sorted(snapshots, key=lambda x: x.get("snapshot_date", date.min)):
            d = s.get("snapshot_date", "?")
            steps = s.get("steps", 0) or 0
            cal = s.get("calories", 0) or 0
            active = s.get("active_minutes", 0) or 0
            sleep = s.get("sleep_hours") or 0
            lines.append(f"  {d}: {steps:,} steps, {cal:,} kcal, {active} min active, {sleep}h sleep")
        return "\n".join(lines)

    @tool_decorator
    def sync_health_data(source: str = "all") -> str:
        """Sync fresh health data from Google Fit and/or Strava.
        source: 'google_fit', 'strava', or 'all'.
        Use this when data seems stale or the user asks to refresh."""
        results = []
        if source in ("all", "google_fit"):
            r = sync_google_fit_for_user(user_id)
            results.append(f"Google Fit: {'synced' if r.get('ok') else r.get('detail', 'failed')}")
        if source == "strava" or (source == "all" and _sync_strava_with_health_all()):
            r = sync_strava_for_user(user_id)
            results.append(f"Strava: {'synced' if r.get('ok') else r.get('detail', 'failed')}")
        elif source == "all":
            results.append("Strava: skipped")
        return " | ".join(results)

    @tool_decorator
    def get_health_insights() -> str:
        """Generate personalized health insights based on today's data.
        Use this when the user asks for advice, suggestions, or health recommendations."""
        snapshots = get_health_snapshots(user_id, source="google_fit", days=1)
        today_snap = next((s for s in snapshots if s.get("snapshot_date") == date.today()), None)
        if not today_snap:
            return "No data available for insights. Sync your health data first."

        insights = []
        steps = today_snap.get("steps") or 0
        active = today_snap.get("active_minutes") or 0
        sleep = today_snap.get("sleep_hours") or 0
        cal = today_snap.get("calories") or 0

        if steps >= 10000:
            insights.append("Great job! You've hit your 10,000 step goal today.")
        elif steps >= 5000:
            remaining = 10000 - steps
            insights.append(f"You're halfway to your step goal. {remaining:,} more steps to go!")
        elif steps > 0:
            insights.append(f"You've taken {steps:,} steps so far. Try a walk to boost your count.")

        if active >= 60:
            insights.append(f"Excellent - {active} active minutes today. You're above the recommended 60 min.")
        elif active > 0:
            insights.append(f"You have {active} active minutes. Aim for at least 60 minutes daily.")

        if sleep >= 7:
            insights.append(f"Well rested with {sleep} hours of sleep.")
        elif sleep > 0:
            insights.append(f"You got {sleep} hours of sleep. Try to get 7-8 hours tonight.")

        if cal > 2000:
            insights.append(f"Good calorie burn today: {cal:,} kcal.")

        return "\n".join(insights) if insights else "Keep going! More data will unlock personalized insights."

    @tool_decorator
    def get_diet_recommendation() -> str:
        """Generate a personalized diet plan and food intake recommendation based on today's health data.
        Use this when the user asks about diet, nutrition, what to eat, meal plan, or food intake.
        ALWAYS start with the medical disclaimer."""
        return _build_diet_recommendation(user_id)

    @tool_decorator
    def get_yoga_recommendation() -> str:
        """Recommend yoga poses based on the user's current health data.
        Use this when the user asks about yoga, stretching, or physical wellness recommendations."""
        snapshots = get_health_snapshots(user_id, source="google_fit", days=1)
        today_snap = next((s for s in snapshots if s.get("snapshot_date") == date.today()), None)

        sleep = (today_snap.get("sleep_hours") or 0) if today_snap else 0
        active = (today_snap.get("active_minutes") or 0) if today_snap else 0
        steps = (today_snap.get("steps") or 0) if today_snap else 0

        recs = ["Yoga Recommendations (from Mental Peace section):", ""]

        if sleep < 6:
            recs.append("For Better Sleep:")
            recs.append("  - Legs Up The Wall (Viparita Karani) - 5 min")
            recs.append("  - Corpse Pose (Savasana) with deep breathing - 10 min")
            recs.append("  - Child's Pose (Balasana) - 3 min")
            recs.append("")

        if active < 30:
            recs.append("For Energy & Activation:")
            recs.append("  - Sun Salutation (Surya Namaskar) - 5 rounds")
            recs.append("  - Warrior I & II (Virabhadrasana) - 1 min each side")
            recs.append("  - Tree Pose (Vrksasana) - 1 min each side")
            recs.append("")

        if steps > 8000 or active > 45:
            recs.append("For Recovery After Activity:")
            recs.append("  - Downward Dog (Adho Mukha Svanasana) - 1 min")
            recs.append("  - Pigeon Pose (Eka Pada Rajakapotasana) - 2 min each side")
            recs.append("  - Seated Forward Bend (Paschimottanasana) - 2 min")
            recs.append("")

        recs.append("General Daily Practice:")
        recs.append("  - Cat-Cow Stretch (Marjaryasana-Bitilasana) - 2 min")
        recs.append("  - Mountain Pose (Tadasana) with breathing - 3 min")
        recs.append("  - Meditation with Box Breathing - 5 min")
        recs.append("")
        recs.append("Visit the Mental Peace section for guided sessions.")

        return "\n".join(recs)

    task_tools = make_task_tools(tool_decorator, user_id, source_name="Health")
    return [get_todays_health, get_weekly_health, sync_health_data, get_health_insights, get_diet_recommendation, get_yoga_recommendation] + task_tools


from functools import lru_cache

@lru_cache(maxsize=64)
def _build_health_graph(user_id: str, model_override: Optional[str] = None):
    deps = _require_deps()
    AIMessage = deps["AIMessage"]
    SystemMessage = deps["SystemMessage"]
    ToolMessage = deps["ToolMessage"]
    StateGraph = deps["StateGraph"]
    END = deps["END"]

    tools = _health_toolset(deps["tool"], user_id)
    tool_map = {t.name: t for t in tools}
    mutation_tools = {"sync_health_data"}

    def call_model(state: HealthAgentState) -> HealthAgentState:
        llm = _get_llm(model_override=model_override, user_id=user_id)
        llm_with_tools = llm.bind_tools(tools)
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        sem = (state.get("semantic_context") or "").strip()
        context = f"\nRelevant context from memory:\n{sem}\n" if sem else ""
        system = f"{HEALTH_AGENT_SYSTEM_PROMPT}\nCurrent time: {now}{context}"
        full = [SystemMessage(content=system)] + list(state["messages"])
        response = llm_with_tools.invoke(full)
        return {**state, "messages": [response]}

    def call_tools(state: HealthAgentState) -> HealthAgentState:
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
                    if name in mutation_tools:
                        mutated = True
                except Exception as exc:
                    result = f"Error running {name}: {exc}"
            out.append(ToolMessage(content=str(result), tool_call_id=tid))
        return {**state, "messages": out, "mutated": mutated}

    def should_continue(state: HealthAgentState):
        last = state["messages"][-1]
        rounds = sum(1 for m in state["messages"] if hasattr(m, "tool_calls") and m.tool_calls)
        if rounds >= 6:
            return "end"
        if hasattr(last, "tool_calls") and last.tool_calls:
            return "call_tools"
        return "end"

    wf = StateGraph(HealthAgentState)
    wf.add_node("call_model", call_model)
    wf.add_node("call_tools", call_tools)
    wf.set_entry_point("call_model")
    wf.add_conditional_edges("call_model", should_continue, {"call_tools": "call_tools", "end": END})
    wf.add_edge("call_tools", "call_model")
    return wf.compile(), AIMessage


def run_health_agent_chat(
    query: str,
    history: List[dict],
    user_id: Optional[str],
    model: Optional[str] = None,
    preloaded_context: Optional[str] = None,
) -> Dict:
    if not user_id:
        return {"response": "User session is missing. Please sign in again.", "success": False,
                "delegated_to": "health-subagent", "refresh_health": False}

    if _is_diet_query(query):
        try:
            content = _build_diet_recommendation(user_id)
            try:
                from ..memory.service import memory_service
                memory_service.store_turn(user_id, query, content)
            except Exception:
                pass
            return {
                "response": content,
                "success": True,
                "delegated_to": "health-subagent",
                "refresh_health": False,
            }
        except Exception as exc:
            log.error("Diet recommendation failed: %s", exc, exc_info=True)

    from ..llm_factory import is_any_llm_configured
    if not is_any_llm_configured(user_id):
        return {"response": "Health sub-agent is unavailable - no LLM provider configured. Go to Settings to add one.",
                "success": True, "delegated_to": "health-subagent", "refresh_health": False}

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
                        domains=["health"],
                        qdrant_collections=["health", "tasks", "memory"],
                        days_per_domain={"health": 8, "tasks": 7},
                        token_budget={"health": 2200, "tasks": 1000, "memory": 800},
                    )
                    semantic_context = assemble_context(user_id, plan).text
                except Exception:
                    semantic_context = memory_service.build_context_for_query(user_id, query)
        except Exception:
            semantic_context = ""

        graph, _ = _build_health_graph(user_id, model)

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

        initial_state: HealthAgentState = {
            "messages": history_messages + [HumanMessage(content=query)],
            "user_query": query,
            "user_id": user_id,
            "semantic_context": semantic_context,
            "mutated": False,
        }

        result = graph.invoke(initial_state)
        messages = result.get("messages", [])
        if not messages:
            raise RuntimeError("No response produced by Health sub-agent")

        final = messages[-1]
        content = getattr(final, "content", str(final))
        if isinstance(content, list):
            content = "\n".join(str(part) for part in content)

        mutated = bool(result.get("mutated", False))

        if user_id and str(content).strip():
            try:
                from ..memory.service import memory_service
                memory_service.store_turn(user_id, query, str(content))
            except Exception:
                pass

        return {
            "response": str(content),
            "success": True,
            "delegated_to": "health-subagent",
            "refresh_health": mutated,
        }

    except Exception as exc:
        log.error("Health sub-agent error: %s", exc, exc_info=True)
        return {
            "response": f"Health sub-agent encountered an error: {exc}",
            "success": False,
            "delegated_to": "health-subagent",
            "refresh_health": False,
        }
