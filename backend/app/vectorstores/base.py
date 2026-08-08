"""Vector-store protocol."""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from app.rag.types import ChunkRecord, RetrievedDocument


class VectorStore(Protocol):
    async def ensure_collection(self, dimension: int) -> None: ...

    async def health(self) -> bool: ...

    async def upsert(self, chunks: list[ChunkRecord]) -> None: ...

    async def delete_document(self, document_id: UUID) -> None: ...

    async def hybrid_search(
        self,
        query: str,
        query_vector: list[float],
        *,
        filters: dict[str, object],
        top_k: int,
    ) -> list[RetrievedDocument]: ...

