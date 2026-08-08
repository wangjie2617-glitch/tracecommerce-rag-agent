"""Typed records shared by ingestion, retrieval, and the Agent."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ParsedDocument(BaseModel):
    """Normalized document before chunking."""

    title: str
    source_url: str
    source_type: str
    content: str
    language: str = "zh-CN"
    country_or_region: str | None = None
    business_category: str | None = None
    published_at: datetime | None = None
    crawled_at: datetime


class ChunkRecord(BaseModel):
    """One structure-aware chunk plus traceability metadata."""

    id: str
    chunk_id: UUID
    document_id: UUID
    source_id: UUID
    company_name: str
    source_type: str
    title: str
    section_title: str | None = None
    source_url: str
    content: str
    language: str
    country_or_region: str | None = None
    business_category: str | None = None
    published_at: datetime | None = None
    crawled_at: datetime
    content_hash: str
    version: int
    is_active: bool = True
    dense_vector: list[float] = Field(default_factory=list)


class RetrievedDocument(BaseModel):
    """Search result used by reranking and citation building."""

    chunk_id: UUID
    document_id: UUID
    source_id: UUID
    company_name: str
    source_type: str
    title: str
    section_title: str | None = None
    source_url: str
    content: str
    language: str
    country_or_region: str | None = None
    business_category: str | None = None
    version: int
    is_active: bool
    crawled_at: datetime
    retrieval_score: float
    rerank_score: float | None = None
