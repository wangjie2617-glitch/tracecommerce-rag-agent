"""LangGraph state contract."""

from __future__ import annotations

from typing import Any, TypedDict


class AgentState(TypedDict, total=False):
    request_id: str
    thread_id: str
    user_id: str
    role: str
    original_query: str
    rewritten_query: str
    language: str
    intent: str
    region: str | None
    filters: dict[str, Any]
    retrieved_documents: list[dict[str, Any]]
    reranked_documents: list[dict[str, Any]]
    evidence_score: float
    evidence_level: str
    evidence_sufficient: bool
    answer: str
    citations: list[dict[str, Any]]
    confidence: float
    grounded: bool
    risk_flags: list[str]
    execution_trace: list[dict[str, Any]]
    warnings: list[str]
    retry_count: int
    error: str | None
