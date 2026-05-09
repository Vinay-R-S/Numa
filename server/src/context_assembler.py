"""
Context Assembler - executes a RetrievalPlan and assembles LLM context.

Queries multiple Qdrant collections in parallel, deduplicates results,
applies token-budget-aware truncation, and formats a structured context
block for agent injection.

Usage::

    from src.context_assembler import assemble_context
    from src.data_planner import plan_retrieval

    plan = plan_retrieval(user_id, query)
    ctx = assemble_context(user_id, plan)
    # ctx.text is the formatted context string ready for the LLM
"""
from __future__ import annotations

import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Dict, List, Optional

log = logging.getLogger(__name__)


@dataclass
class AssembledContext:
    """Result of context assembly."""
    text: str                          # formatted context for LLM
    token_estimate: int                # rough token count (chars / 4)
    sources: Dict[str, int]            # {"calendar": 4, "slack": 3}
    retrieval_ms: float                # total retrieval time in ms


def _estimate_tokens(text: str) -> int:
    """Rough token estimate: ~4 chars per token for English text."""
    return max(1, len(text) // 4)


def _truncate_to_budget(text: str, max_tokens: int) -> str:
    """Truncate text to approximately fit within max_tokens."""
    max_chars = max_tokens * 4
    if len(text) <= max_chars:
        return text
    # Truncate at last newline before the limit to avoid cutting mid-line
    truncated = text[:max_chars]
    last_nl = truncated.rfind("\n")
    if last_nl > max_chars * 0.5:
        truncated = truncated[:last_nl]
    return truncated + "\n[...truncated]"


def _query_qdrant_collection(
    user_id: str,
    collection_type: str,
    query_vector: List[float],
    limit: int,
) -> List[dict]:
    """Query a single Qdrant collection and return payload dicts."""
    try:
        from src.memory.service import memory_service
    except ImportError:
        from .memory.service import memory_service

    deps = memory_service._deps()
    qdrant = memory_service._qdrant_client()
    if not deps or not qdrant:
        return []

    collection_name = memory_service.user_collection_name(user_id, collection_type)

    try:
        if not qdrant.collection_exists(collection_name):
            return []

        user_filter = deps["Filter"](
            must=[
                deps["FieldCondition"](
                    key="user_id",
                    match=deps["MatchValue"](value=user_id),
                )
            ]
        )

        hits = qdrant.search(
            collection_name=collection_name,
            query_vector=query_vector,
            query_filter=user_filter,
            limit=limit,
            with_payload=True,
        )

        results = []
        for hit in hits:
            payload = getattr(hit, "payload", None) or {}
            payload["_score"] = getattr(hit, "score", 0.0)
            payload["_collection"] = collection_type
            results.append(payload)
        return results
    except Exception as exc:
        log.warning("Qdrant query failed for %s/%s: %s", user_id, collection_type, exc)
        return []


def _format_calendar_results(results: List[dict]) -> str:
    if not results:
        return ""
    lines = ["[Calendar Events]"]
    for r in results:
        title = r.get("title") or r.get("summary") or "(No title)"
        start = r.get("start_at", "")
        end = r.get("end_at", "")
        desc = r.get("description", "")
        entry = f"  • {title}"
        if start:
            entry += f" | {start[:16]}"
        if end:
            entry += f" → {end[11:16]}"
        if desc:
            entry += f" | {desc[:60]}"
        lines.append(entry)
    return "\n".join(lines)


def _format_slack_results(results: List[dict]) -> str:
    if not results:
        return ""
    lines = ["[Slack Messages]"]
    for r in results:
        ch = r.get("channel_name", "?")
        text = (r.get("text", "") or "")[:150]
        ts = r.get("created_at", "")[:10]
        lines.append(f"  • #{ch}: {text} ({ts})")
    return "\n".join(lines)


def _format_memory_results(results: List[dict]) -> str:
    if not results:
        return ""
    lines = ["[Prior Conversations]"]
    for r in results:
        text = (r.get("text", "") or "")[:200]
        lines.append(f"  • {text}")
    return "\n".join(lines)


_FORMATTERS = {
    "calendar": _format_calendar_results,
    "slack": _format_slack_results,
    "memory": _format_memory_results,
}


def assemble_context(
    user_id: str,
    plan,  # RetrievalPlan from data_planner
    pre_fetched: Optional[str] = None,
) -> AssembledContext:
    """
    Execute the retrieval plan and assemble a formatted context block.

    If *pre_fetched* is provided (e.g., from master agent delegation),
    Qdrant queries are skipped entirely.
    """
    start_time = time.monotonic()

    # Short-circuit if context already available or Qdrant should be skipped
    if pre_fetched:
        return AssembledContext(
            text=pre_fetched,
            token_estimate=_estimate_tokens(pre_fetched),
            sources={"pre_fetched": 1},
            retrieval_ms=0.0,
        )

    if plan.skip_qdrant or not plan.qdrant_collections:
        return AssembledContext(
            text="",
            token_estimate=0,
            sources={},
            retrieval_ms=0.0,
        )

    # Embed the query once (shared across all collection searches)
    try:
        from src.embedder import embedder
    except ImportError:
        from .embedder import embedder

    query_vector = embedder.embed(plan.query.strip())
    if not query_vector:
        return AssembledContext(text="", token_estimate=0, sources={},
                               retrieval_ms=0.0)

    # Determine per-collection result limits from token budget
    collection_limits: Dict[str, int] = {}
    for coll in plan.qdrant_collections:
        budget = plan.token_budget.get(coll, 1000)
        # ~200 tokens per result → budget / 200
        collection_limits[coll] = max(2, min(budget // 200, 8))

    # Query collections in parallel
    all_results: Dict[str, List[dict]] = {}
    max_workers = min(len(plan.qdrant_collections), 4)

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {
            pool.submit(
                _query_qdrant_collection,
                user_id,
                coll,
                query_vector,
                collection_limits.get(coll, 4),
            ): coll
            for coll in plan.qdrant_collections
        }
        for future in as_completed(futures):
            coll = futures[future]
            try:
                all_results[coll] = future.result()
            except Exception as exc:
                log.warning("Context assembly failed for %s: %s", coll, exc)
                all_results[coll] = []

    # Format and truncate per-domain results
    sections: List[str] = []
    sources: Dict[str, int] = {}

    for coll in plan.qdrant_collections:
        results = all_results.get(coll, [])
        if not results:
            continue

        formatter = _FORMATTERS.get(coll, _format_memory_results)
        formatted = formatter(results)

        if formatted:
            budget = plan.token_budget.get(coll, 1000)
            formatted = _truncate_to_budget(formatted, budget)
            sections.append(formatted)
            sources[coll] = len(results)

    final_text = "\n\n".join(sections)

    elapsed_ms = (time.monotonic() - start_time) * 1000

    return AssembledContext(
        text=final_text,
        token_estimate=_estimate_tokens(final_text),
        sources=sources,
        retrieval_ms=round(elapsed_ms, 1),
    )
