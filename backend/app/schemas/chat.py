"""Chat, citation, conversation, feedback, and trace schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class ChatQueryRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    thread_id: UUID | None = None
    filters: dict[str, Any] = Field(default_factory=dict)

    @field_validator("query")
    @classmethod
    def clean_query(cls, value: str) -> str:
        normalized = " ".join(value.split())
        if not normalized:
            raise ValueError("query 不能为空")
        return normalized


class CitationData(BaseModel):
    document_id: UUID
    chunk_id: UUID
    title: str
    section_title: str | None
    source_url: str
    quoted_text: str
    retrieval_score: float
    rerank_score: float | None
    crawled_at: datetime


class TraceStepData(BaseModel):
    node: str
    status: str
    duration_ms: float
    started_at: datetime
    ended_at: datetime
    input_summary: str | None = None
    output_summary: str | None = None
    error: str | None = None


class ChatAnswerData(BaseModel):
    request_id: UUID
    thread_id: UUID
    answer: str
    evidence_score: float = Field(
        ge=0.0,
        le=1.0,
        description="启发式证据匹配分，不代表答案正确概率",
    )
    evidence_level: Literal["insufficient", "low", "medium", "high"]
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        deprecated=True,
        description="兼容旧客户端；请改用 evidence_score",
    )
    grounded: bool
    intent: str
    language: str
    citations: list[CitationData]
    trace: list[TraceStepData]
    warnings: list[str]


class ConversationSummary(BaseModel):
    thread_id: UUID
    title: str | None
    created_at: datetime
    updated_at: datetime


class MessageData(BaseModel):
    id: UUID
    role: str
    content: str
    request_id: UUID | None
    created_at: datetime


class ConversationDetail(BaseModel):
    thread_id: UUID
    title: str | None
    messages: list[MessageData]


class FeedbackRequest(BaseModel):
    request_id: UUID
    helpful: bool
    comment: str | None = Field(default=None, max_length=1000)


class FeedbackData(BaseModel):
    id: UUID
    request_id: UUID
    helpful: bool


class RequestTraceData(BaseModel):
    result: ChatAnswerData
    retrieved: list[dict[str, Any]]
