"""Knowledge source and document API schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator

SourceType = Literal["website", "pdf", "txt", "markdown", "html", "docx"]


class KnowledgeSourceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    company_name: str = Field(min_length=1, max_length=200)
    source_type: SourceType
    base_url: HttpUrl | None = None
    config: dict = Field(default_factory=dict)

    @model_validator(mode="after")
    def require_url_for_website(self) -> KnowledgeSourceCreate:
        if self.source_type == "website" and self.base_url is None:
            raise ValueError("website 知识源必须提供 base_url")
        return self


class KnowledgeSourceUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    base_url: HttpUrl | None = None
    config: dict | None = None
    is_active: bool | None = None


class KnowledgeSourceData(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    company_name: str
    source_type: str
    base_url: str | None
    config: dict
    is_active: bool
    last_synced_at: datetime | None
    created_at: datetime
    updated_at: datetime


class IngestionJobData(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    source_id: UUID | None
    status: str
    pages_discovered: int
    documents_created: int
    documents_updated: int
    documents_unchanged: int
    chunks_written: int
    error: str | None
    started_at: datetime | None
    finished_at: datetime | None


class DocumentData(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    source_id: UUID
    title: str
    source_url: str
    source_type: str
    language: str
    country_or_region: str | None
    business_category: str | None
    content_hash: str
    current_version: int
    is_active: bool
    crawled_at: datetime
    created_at: datetime
    updated_at: datetime


class DocumentListData(BaseModel):
    items: list[DocumentData]
    count: int
