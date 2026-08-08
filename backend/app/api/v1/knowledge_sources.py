"""Knowledge source CRUD and synchronization endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.db.models import User
from app.db.session import get_session
from app.dependencies import get_embedding_provider, get_vector_store, require_roles
from app.rag.embeddings import EmbeddingProvider
from app.schemas.common import ApiResponse
from app.schemas.knowledge import (
    IngestionJobData,
    KnowledgeSourceCreate,
    KnowledgeSourceData,
    KnowledgeSourceUpdate,
)
from app.services.knowledge import KnowledgeService
from app.vectorstores.base import VectorStore

router = APIRouter()
AdminUser = Annotated[User, Depends(require_roles("admin"))]


def _service(
    session: AsyncSession,
    settings: Settings,
    embedding: EmbeddingProvider,
    vector_store: VectorStore,
) -> KnowledgeService:
    return KnowledgeService(session, settings, embedding, vector_store)


@router.post("", response_model=ApiResponse[KnowledgeSourceData], status_code=status.HTTP_201_CREATED)
async def create_source(
    payload: KnowledgeSourceCreate,
    request: Request,
    _: AdminUser,
    session: Annotated[AsyncSession, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
    embedding: Annotated[EmbeddingProvider, Depends(get_embedding_provider)],
    vector_store: Annotated[VectorStore, Depends(get_vector_store)],
) -> ApiResponse[KnowledgeSourceData]:
    source = await _service(session, settings, embedding, vector_store).create_source(payload)
    return ApiResponse(request_id=request.state.request_id, data=KnowledgeSourceData.model_validate(source))


@router.get("", response_model=ApiResponse[list[KnowledgeSourceData]])
async def list_sources(
    request: Request,
    _: Annotated[User, Depends(require_roles("admin", "customer_service", "operator"))],
    session: Annotated[AsyncSession, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
    embedding: Annotated[EmbeddingProvider, Depends(get_embedding_provider)],
    vector_store: Annotated[VectorStore, Depends(get_vector_store)],
) -> ApiResponse[list[KnowledgeSourceData]]:
    sources = await _service(session, settings, embedding, vector_store).list_sources()
    return ApiResponse(
        request_id=request.state.request_id,
        data=[KnowledgeSourceData.model_validate(source) for source in sources],
    )


@router.get("/jobs", response_model=ApiResponse[list[IngestionJobData]])
async def list_sync_jobs(
    request: Request,
    _: Annotated[User, Depends(require_roles("admin", "operator"))],
    session: Annotated[AsyncSession, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
    embedding: Annotated[EmbeddingProvider, Depends(get_embedding_provider)],
    vector_store: Annotated[VectorStore, Depends(get_vector_store)],
    source_id: UUID | None = None,
) -> ApiResponse[list[IngestionJobData]]:
    jobs = await _service(session, settings, embedding, vector_store).list_jobs(source_id)
    return ApiResponse(
        request_id=request.state.request_id,
        data=[IngestionJobData.model_validate(job) for job in jobs],
    )


@router.get("/jobs/{job_id}", response_model=ApiResponse[IngestionJobData])
async def get_sync_job(
    job_id: UUID,
    request: Request,
    _: Annotated[User, Depends(require_roles("admin", "operator"))],
    session: Annotated[AsyncSession, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
    embedding: Annotated[EmbeddingProvider, Depends(get_embedding_provider)],
    vector_store: Annotated[VectorStore, Depends(get_vector_store)],
) -> ApiResponse[IngestionJobData]:
    job = await _service(session, settings, embedding, vector_store).get_job(job_id)
    return ApiResponse(request_id=request.state.request_id, data=IngestionJobData.model_validate(job))


@router.get("/{source_id}", response_model=ApiResponse[KnowledgeSourceData])
async def get_source(
    source_id: UUID,
    request: Request,
    _: Annotated[User, Depends(require_roles("admin", "customer_service", "operator"))],
    session: Annotated[AsyncSession, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
    embedding: Annotated[EmbeddingProvider, Depends(get_embedding_provider)],
    vector_store: Annotated[VectorStore, Depends(get_vector_store)],
) -> ApiResponse[KnowledgeSourceData]:
    source = await _service(session, settings, embedding, vector_store).get_source(source_id)
    return ApiResponse(request_id=request.state.request_id, data=KnowledgeSourceData.model_validate(source))


@router.patch("/{source_id}", response_model=ApiResponse[KnowledgeSourceData])
async def update_source(
    source_id: UUID,
    payload: KnowledgeSourceUpdate,
    request: Request,
    _: AdminUser,
    session: Annotated[AsyncSession, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
    embedding: Annotated[EmbeddingProvider, Depends(get_embedding_provider)],
    vector_store: Annotated[VectorStore, Depends(get_vector_store)],
) -> ApiResponse[KnowledgeSourceData]:
    source = await _service(session, settings, embedding, vector_store).update_source(source_id, payload)
    return ApiResponse(request_id=request.state.request_id, data=KnowledgeSourceData.model_validate(source))


@router.delete("/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
async def disable_source(
    source_id: UUID,
    _: AdminUser,
    session: Annotated[AsyncSession, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
    embedding: Annotated[EmbeddingProvider, Depends(get_embedding_provider)],
    vector_store: Annotated[VectorStore, Depends(get_vector_store)],
) -> None:
    await _service(session, settings, embedding, vector_store).disable_source(source_id)


@router.post("/{source_id}/sync", response_model=ApiResponse[IngestionJobData])
async def sync_source(
    source_id: UUID,
    request: Request,
    _: AdminUser,
    session: Annotated[AsyncSession, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
    embedding: Annotated[EmbeddingProvider, Depends(get_embedding_provider)],
    vector_store: Annotated[VectorStore, Depends(get_vector_store)],
) -> ApiResponse[IngestionJobData]:
    job = await _service(session, settings, embedding, vector_store).sync_source(source_id)
    return ApiResponse(request_id=request.state.request_id, data=IngestionJobData.model_validate(job))
