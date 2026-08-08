"""In-memory hybrid vector store for tests and offline development."""

from __future__ import annotations

import math
from uuid import UUID

from app.rag.tokenization import tokenize_for_retrieval
from app.rag.types import ChunkRecord, RetrievedDocument


def _cosine(left: list[float], right: list[float]) -> float:
    if not left or len(left) != len(right):
        return 0.0
    dot = sum(a * b for a, b in zip(left, right, strict=True))
    left_norm = math.sqrt(sum(value * value for value in left)) or 1.0
    right_norm = math.sqrt(sum(value * value for value in right)) or 1.0
    return dot / (left_norm * right_norm)


class InMemoryVectorStore:
    """Deterministic dense + keyword weighted search implementation."""

    def __init__(self) -> None:
        self._records: dict[str, ChunkRecord] = {}
        self._dimension: int | None = None

    async def ensure_collection(self, dimension: int) -> None:
        self._dimension = dimension

    async def health(self) -> bool:
        return True

    async def upsert(self, chunks: list[ChunkRecord]) -> None:
        for chunk in chunks:
            if self._dimension is not None and len(chunk.dense_vector) != self._dimension:
                raise ValueError("向量维度与 Collection 不一致")
            self._records[chunk.id] = chunk.model_copy(deep=True)

    async def delete_document(self, document_id: UUID) -> None:
        keys = [key for key, value in self._records.items() if value.document_id == document_id]
        for key in keys:
            del self._records[key]

    @staticmethod
    def _matches(chunk: ChunkRecord, filters: dict[str, object]) -> bool:
        for key, expected in filters.items():
            if expected is None:
                continue
            actual = getattr(chunk, key, None)
            if isinstance(expected, list):
                if actual not in expected:
                    return False
            elif actual != expected:
                return False
        return True

    async def hybrid_search(
        self,
        query: str,
        query_vector: list[float],
        *,
        filters: dict[str, object],
        top_k: int,
    ) -> list[RetrievedDocument]:
        query_tokens = set(tokenize_for_retrieval(query))
        scored: list[tuple[float, ChunkRecord]] = []
        for chunk in self._records.values():
            if not chunk.is_active or not self._matches(chunk, filters):
                continue
            dense = max(_cosine(query_vector, chunk.dense_vector), 0.0)
            content_tokens = set(tokenize_for_retrieval(chunk.content))
            sparse = len(query_tokens & content_tokens) / max(len(query_tokens), 1)
            scored.append((0.7 * dense + 0.3 * sparse, chunk))
        scored.sort(key=lambda item: item[0], reverse=True)
        return [
            RetrievedDocument(
                **chunk.model_dump(exclude={"id", "content_hash", "published_at", "dense_vector"}),
                retrieval_score=round(float(score), 6),
            )
            for score, chunk in scored[:top_k]
        ]
