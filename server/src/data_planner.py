"""
Data Planner - zero-LLM-cost query analysis for smart retrieval.

Analyzes the user's query using keyword/pattern matching to determine
which data domains are relevant, how many days to retrieve, and
token budget allocation. No LLM call is made.

Usage::

    from src.data_planner import plan_retrieval
    plan = plan_retrieval(user_id, "How was my week?")
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional

DEFAULT_RETRIEVAL_DAYS = int(os.getenv("DEFAULT_RETRIEVAL_DAYS", "7"))
MAX_RETRIEVAL_DAYS = int(os.getenv("MAX_RETRIEVAL_DAYS", "30"))
MASTER_TOKEN_BUDGET = int(os.getenv("MASTER_AGENT_TOKEN_BUDGET", "6000"))

_DOMAIN_KEYWORDS: Dict[str, List[str]] = {
    "calendar": [
        "calendar", "event", "meeting", "schedule", "appointment",
        "free slot", "reschedule", "cancel event", "agenda", "upcoming",
        "book", "invite", "attendee", "google meet", "busy",
    ],
    "slack": [
        "slack", "message", "channel", "standup", "thread",
        "dm", "direct message", "discussed", "conversation", "workspace",
    ],
    "health": [
        "health", "steps", "calories", "sleep", "active",
        "fitness", "workout", "exercise", "strava", "google fit",
        "diet", "yoga", "weight", "distance", "walk", "run",
        "heart", "heart rate", "heart points", "bpm",
    ],
    "github": [
        "github", "commit", "pull request", "pr ", "repo",
        "repository", "push", "merge", "branch", "code",
        "contribution", "coding", "issue",
    ],
    "leetcode": [
        "leetcode", "leet code", "coding problem", "dsa",
        "solved", "ranking", "submission", "algorithm",
    ],
    "journal": [
        "journal", "diary", "reflection", "mood",
        "daily summary", "how was my day", "auto-generate", "recap",
    ],
    "tasks": [
        "task", "todo", "to-do", "to do", "remind",
        "deadline", "due date", "checklist", "pending", "planned",
    ],
}

_ACTION_PATTERNS = [
    r"sync\s+(my\s+)?health", r"sync\s+(my\s+)?data",
    r"connect\s+(my\s+)?", r"refresh\s+",
    r"change\s+(my\s+)?settings", r"update\s+(my\s+)?api",
]

_TEMPORAL_PATTERNS: Dict[str, List[str]] = {
    "today": [r"\btoday\b", r"\btoday'?s\b", r"\bthis morning\b",
              r"\bthis afternoon\b", r"\bright now\b", r"\bcurrent(ly)?\b",
              r"\bmy day\b"],
    "week": [r"\bthis week\b", r"\bpast week\b", r"\blast week\b",
             r"\bweekly\b", r"\b7 days?\b", r"\bmy week\b"],
    "month": [r"\bthis month\b", r"\bpast month\b", r"\blast month\b",
              r"\bmonthly\b", r"\b30 days?\b", r"\bmy month\b"],
    "yesterday": [r"\byesterday\b"],
}


@dataclass
class RetrievalPlan:
    """The output of query analysis - tells the system what data to fetch."""
    query: str
    temporal_scope: str
    domains: List[str]
    qdrant_collections: List[str]
    days_per_domain: Dict[str, int]
    token_budget: Dict[str, int]
    skip_qdrant: bool = False
    priority: str = "normal"
    total_token_budget: int = 4000


def _detect_temporal_scope(query: str) -> str:
    q_lower = query.lower()
    for scope, patterns in _TEMPORAL_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, q_lower):
                return scope
    return "general"


def _detect_domains(query: str) -> List[str]:
    q_lower = query.lower()
    matched: List[str] = []
    for domain, keywords in _DOMAIN_KEYWORDS.items():
        for kw in keywords:
            if kw in q_lower:
                matched.append(domain)
                break
    return matched


def _is_action_only(query: str) -> bool:
    q_lower = query.lower()
    return any(re.search(p, q_lower) for p in _ACTION_PATTERNS)


def _is_broad_query(query: str) -> bool:
    broad = [
        r"\bhow was my\b", r"\bsummar(y|ize)\b", r"\boverview\b",
        r"\bmy day\b", r"\bmy week\b", r"\bmy month\b",
        r"\bdashboard\b", r"\bwhat'?s new\b", r"\bprogress\b",
        r"\bgenerate.*journal\b", r"\bauto.?generate\b", r"\brecap\b",
    ]
    q_lower = query.lower()
    return any(re.search(p, q_lower) for p in broad)


def _scope_to_days(scope: str) -> int:
    return {"today": 1, "yesterday": 2, "week": 7, "month": 30,
            "general": DEFAULT_RETRIEVAL_DAYS}.get(scope, DEFAULT_RETRIEVAL_DAYS)


def _allocate_token_budget(domains: List[str], total: int) -> Dict[str, int]:
    if not domains:
        return {"memory": total}
    if len(domains) == 1:
        return {domains[0]: int(total * 0.75), "memory": int(total * 0.25)}
    memory_budget = int(total * 0.15)
    remaining = total - memory_budget
    per_domain = remaining // len(domains)
    result = {d: per_domain for d in domains}
    result["memory"] = memory_budget
    return result


def plan_retrieval(
    user_id: str,
    query: str,
    total_token_budget: int = 0,
) -> RetrievalPlan:
    """Analyze query and produce an optimized retrieval plan (zero LLM cost)."""
    if total_token_budget <= 0:
        total_token_budget = MASTER_TOKEN_BUDGET

    if _is_action_only(query):
        return RetrievalPlan(
            query=query, temporal_scope="today", domains=[],
            qdrant_collections=[], days_per_domain={}, token_budget={},
            skip_qdrant=True, priority="normal",
            total_token_budget=total_token_budget,
        )

    temporal_scope = _detect_temporal_scope(query)
    base_days = _scope_to_days(temporal_scope)
    domains = _detect_domains(query)

    if _is_broad_query(query):
        domains = ["calendar", "health", "slack", "github", "tasks"]
    elif not domains:
        domains = []

    # Deduplicate preserving order
    seen = set()
    domains = [d for d in domains if not (d in seen or seen.add(d))]

    days_per_domain: Dict[str, int] = {}
    for d in domains:
        if d == "calendar":
            days = 30 if temporal_scope in ("month", "general") else base_days
        elif d == "slack":
            days = min(base_days, 7)
        else:
            days = base_days
        days_per_domain[d] = min(days, MAX_RETRIEVAL_DAYS)

    qdrant_collections: List[str] = []
    qdrant_domains = {"calendar", "slack", "health", "github", "tasks", "memory"}
    for d in domains:
        if d in qdrant_domains:
            qdrant_collections.append(d)
    if "memory" not in qdrant_collections:
        qdrant_collections.append("memory")

    token_budget = _allocate_token_budget(domains, total_token_budget)

    q_lower = query.lower()
    priority = "normal"
    if any(w in q_lower for w in ("urgent", "asap", "immediately")):
        priority = "high"
    elif any(w in q_lower for w in ("journal", "summary", "recap")):
        priority = "low"

    return RetrievalPlan(
        query=query, temporal_scope=temporal_scope, domains=domains,
        qdrant_collections=qdrant_collections, days_per_domain=days_per_domain,
        token_budget=token_budget, skip_qdrant=False, priority=priority,
        total_token_budget=total_token_budget,
    )
