"""Configurable embedding providers with deterministic test doubles."""

from __future__ import annotations

import asyncio
import hashlib
import math
from collections.abc import Sequence
from typing import Protocol

from app.rag.tokenization import tokenize_for_retrieval


class EmbeddingProvider(Protocol):
    """Interface implemented by production and fake embedding providers."""

    @property
    def dimension(self) -> int: ...

    async def embed_documents(self, texts: Sequence[str]) -> list[list[float]]: ...

    async def embed_query(self, text: str) -> list[float]: ...


class FakeEmbedding:
    """Deterministic hashed lexical vectors for tests and offline demos."""

    def __init__(self, dimension: int = 128) -> None:
        self._dimension = dimension

    @property
    def dimension(self) -> int:
        return self._dimension

    def _embed(self, text: str) -> list[float]:
        vector = [0.0] * self._dimension
        tokens = tokenize_for_retrieval(text)
        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % self._dimension
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[index] += sign
        norm = math.sqrt(sum(value * value for value in vector)) or 1.0
        return [value / norm for value in vector]

    async def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        return [self._embed(text) for text in texts]

    async def embed_query(self, text: str) -> list[float]:
        return self._embed(text)


class SentenceTransformerEmbedding:
    """Lazy sentence-transformers adapter for BGE-M3 and compatible models."""

    def __init__(
        self,
        model_name: str,
        *,
        device: str = "cpu",
        batch_size: int = 16,
    ) -> None:
        self.model_name = model_name
        self.device = device
        self.batch_size = batch_size
        self._model = None
        self._dimension: int | None = None

    def _load(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self.model_name, device=self.device)
            self._dimension = int(self._model.get_sentence_embedding_dimension())
        return self._model

    @property
    def dimension(self) -> int:
        self._load()
        assert self._dimension is not None
        return self._dimension

    def _encode(self, texts: Sequence[str]) -> list[list[float]]:
        model = self._load()
        values = model.encode(
            list(texts),
            batch_size=self.batch_size,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return values.tolist()

    async def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        return await asyncio.to_thread(self._encode, texts)

    async def embed_query(self, text: str) -> list[float]:
        return (await self.embed_documents([text]))[0]


def create_embedding_provider(
    provider: str,
    *,
    model_name: str,
    device: str,
    batch_size: int,
) -> EmbeddingProvider:
    """Create an embedding provider from configuration."""
    if provider == "fake":
        return FakeEmbedding()
    if provider == "sentence_transformers":
        return SentenceTransformerEmbedding(model_name, device=device, batch_size=batch_size)
    raise ValueError(f"不支持的 Embedding Provider: {provider}")
