"""Rerank retrieved chunks using a cross-encoder or deterministic lexical score."""

from __future__ import annotations

import asyncio
import math
from typing import Protocol

from app.rag.tokenization import tokenize_for_retrieval
from app.rag.types import RetrievedDocument


class Reranker(Protocol):
    async def rerank(
        self,
        query: str,
        documents: list[RetrievedDocument],
        *,
        top_k: int,
    ) -> list[RetrievedDocument]: ...


class MockReranker:
    """Token-overlap reranker used by tests without external model downloads."""

    @staticmethod
    def _tokens(text: str) -> set[str]:
        return set(tokenize_for_retrieval(text))

    async def rerank(
        self,
        query: str,
        documents: list[RetrievedDocument],
        *,
        top_k: int,
    ) -> list[RetrievedDocument]:
        query_tokens = self._tokens(query)
        ranked: list[RetrievedDocument] = []
        for document in documents:
            content_tokens = self._tokens(document.content)
            score = len(query_tokens & content_tokens) / max(len(query_tokens), 1)
            updated = document.model_copy(deep=True)
            updated.rerank_score = round(float(score), 6)
            ranked.append(updated)
        ranked.sort(key=lambda item: item.rerank_score or 0.0, reverse=True)
        return ranked[:top_k]


class CrossEncoderReranker:
    """Lazy BGE cross-encoder reranker."""

    def __init__(self, model_name: str, *, device: str = "cpu") -> None:
        self.model_name = model_name
        self.device = device
        self._model = None

    def _load(self):
        if self._model is None:
            from sentence_transformers import CrossEncoder

            self._model = CrossEncoder(self.model_name, device=self.device)
        return self._model

    def _predict(self, query: str, documents: list[RetrievedDocument]) -> list[float]:
        pairs = [(query, document.content) for document in documents]
        raw = self._load().predict(pairs)
        return [1.0 / (1.0 + math.exp(-float(score))) for score in raw]

    async def rerank(
        self,
        query: str,
        documents: list[RetrievedDocument],
        *,
        top_k: int,
    ) -> list[RetrievedDocument]:
        if not documents:
            return []
        scores = await asyncio.to_thread(self._predict, query, documents)
        ranked: list[RetrievedDocument] = []
        for document, score in zip(documents, scores, strict=True):
            updated = document.model_copy(deep=True)
            updated.rerank_score = round(score, 6)
            ranked.append(updated)
        ranked.sort(key=lambda item: item.rerank_score or 0.0, reverse=True)
        return ranked[:top_k]


def create_reranker(provider: str, *, model_name: str, device: str) -> Reranker:
    if provider == "mock":
        return MockReranker()
    if provider == "cross_encoder":
        return CrossEncoderReranker(model_name, device=device)
    raise ValueError(f"不支持的 Reranker Provider: {provider}")
