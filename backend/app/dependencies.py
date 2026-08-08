"""FastAPI dependencies, RBAC guards, and dependency health probes."""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from functools import lru_cache
from typing import Annotated
from uuid import UUID

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.exceptions import AuthenticationError, AuthorizationError
from app.core.logging import user_id_context
from app.core.security import decode_access_token
from app.db.models import User
from app.db.session import SessionFactory, get_session
from app.rag.embeddings import EmbeddingProvider, create_embedding_provider
from app.rag.evaluator import EvidenceEvaluator
from app.rag.llm import LLMProvider, create_llm_provider
from app.rag.reranker import Reranker, create_reranker
from app.rag.retriever import HybridRetriever
from app.repositories.users import UserRepository
from app.vectorstores.base import VectorStore
from app.vectorstores.memory import InMemoryVectorStore

bearer = HTTPBearer(auto_error=False)


@lru_cache
def get_embedding_provider() -> EmbeddingProvider:
    settings = get_settings()
    return create_embedding_provider(
        settings.embedding_provider,
        model_name=settings.embedding_model,
        device=settings.embedding_device,
        batch_size=settings.embedding_batch_size,
    )


@lru_cache
def get_reranker() -> Reranker:
    settings = get_settings()
    return create_reranker(
        settings.reranker_provider,
        model_name=settings.reranker_model,
        device=settings.reranker_device,
    )


@lru_cache
def get_vector_store() -> VectorStore:
    settings = get_settings()
    if settings.vector_store_provider == "memory":
        return InMemoryVectorStore()
    if settings.vector_store_provider == "milvus":
        from app.vectorstores.milvus_store import MilvusVectorStore

        return MilvusVectorStore(
            settings.milvus_uri,
            settings.milvus_collection,
            token=settings.milvus_token,
        )
    raise ValueError(f"不支持的 Vector Store Provider: {settings.vector_store_provider}")


@lru_cache
def get_llm_provider() -> LLMProvider:
    settings = get_settings()
    return create_llm_provider(
        settings.llm_provider,
        model=settings.llm_model,
        base_url=settings.llm_base_url,
        api_key=settings.llm_api_key,
        timeout=settings.llm_timeout_seconds,
    )


@lru_cache
def get_agent_graph():
    """Build one process-level graph with InMemorySaver for short-term threads."""
    from app.agents.graph import build_agent_graph
    from app.agents.nodes.core import AgentNodes

    settings = get_settings()
    nodes = AgentNodes(
        llm=get_llm_provider(),
        retriever=HybridRetriever(
            get_embedding_provider(),
            get_vector_store(),
            minimum_score=settings.min_retrieval_score,
        ),
        reranker=get_reranker(),
        evaluator=EvidenceEvaluator(settings.min_evidence_score),
        retrieval_top_k=settings.retrieval_top_k,
        rerank_top_k=settings.rerank_top_k,
    )
    return build_agent_graph(nodes)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AsyncIterator[User]:
    """Resolve the current active user from a Bearer access token."""
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise AuthenticationError("缺少 Bearer Access Token")
    payload = decode_access_token(credentials.credentials)
    try:
        user_id = UUID(str(payload["sub"]))
    except (ValueError, KeyError) as exc:
        raise AuthenticationError("Access Token 用户标识无效") from exc
    user = await UserRepository(session).get_by_id(user_id)
    if user is None or not user.is_active:
        raise AuthenticationError("用户不存在或已停用")
    token = user_id_context.set(str(user.id))
    try:
        yield user
    finally:
        user_id_context.reset(token)


def require_roles(*allowed_roles: str) -> Callable:
    """Return a dependency that permits at least one specified role."""

    async def guard(user: Annotated[User, Depends(get_current_user)]) -> User:
        actual = {role.name for role in user.roles}
        if not actual.intersection(allowed_roles):
            raise AuthorizationError()
        return user

    return guard


async def dependency_health() -> dict[str, str]:
    """Probe PostgreSQL/SQLite and report configured vector-store state."""
    try:
        async with SessionFactory() as session:
            await session.execute(text("SELECT 1"))
        database = "ok"
    except Exception:
        database = "unavailable"
    try:
        vector_store = "ok" if await get_vector_store().health() else "unavailable"
    except Exception:
        vector_store = "unavailable"
    status = "ready" if database == "ok" and vector_store == "ok" else "not_ready"
    return {"status": status, "database": database, "vector_store": vector_store}
