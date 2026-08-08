"""Shared API response schemas."""

from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    """Uniform successful response envelope."""

    model_config = ConfigDict(from_attributes=True)

    success: bool = True
    request_id: str
    data: T


class HealthData(BaseModel):
    status: str
    service: str
    environment: str


class ReadyData(BaseModel):
    status: str
    database: str
    vector_store: str


class MetricsData(BaseModel):
    service: str
    status: str

