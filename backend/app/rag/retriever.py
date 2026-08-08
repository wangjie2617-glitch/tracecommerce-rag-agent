"""Hybrid retrieval orchestration."""

from __future__ import annotations

from app.rag.embeddings import EmbeddingProvider
from app.rag.types import RetrievedDocument
from app.vectorstores.base import VectorStore


class HybridRetriever:
    """Embed a query, search Milvus, and apply a minimum score."""

    def __init__(
        self,
        embedding: EmbeddingProvider,
        vector_store: VectorStore,
        *,
        minimum_score: float = 0.35,
    ) -> None:
        self.embedding = embedding
        self.vector_store = vector_store
        self.minimum_score = minimum_score

    async def retrieve(
        self,
        query: str,
        *,
        filters: dict[str, object],
        top_k: int,
    ) -> list[RetrievedDocument]:
        vector = await self.embedding.embed_query(query)
        results = await self.vector_store.hybrid_search(
            query,
            vector,
            filters=filters,
            top_k=top_k,
        )
        return [item for item in results if item.retrieval_score >= self.minimum_score]

