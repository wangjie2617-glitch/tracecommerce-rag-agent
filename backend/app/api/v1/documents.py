"""Document upload, listing, inspection, and soft deletion endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.core.exceptions import NotFoundError
from app.db.models import User
from app.db.session import get_session
from app.dependencies import get_embedding_provider, get_vector_store, require_roles
from app.rag.embeddings import EmbeddingProvider
from app.repositories.knowledge import KnowledgeRepository
from app.schemas.common import ApiResponse
from app.schemas.knowledge import DocumentData, DocumentListData, IngestionJobData
from app.services.knowledge import KnowledgeService
from app.vectorstores.base import VectorStore

router = APIRouter()
AdminUser = Annotated[User, Depends(require_roles("admin"))]


@router.post("/upload", response_model=ApiResponse[IngestionJobData], status_code=status.HTTP_201_CREATED)
async def upload_document(
    request: Request,
    _: AdminUser,
    source_id: Annotated[UUID, Form()],
    file: Annotated[UploadFile, File()],
    session: Annotated[AsyncSession, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
    embedding: Annotated[EmbeddingProvider, Depends(get_embedding_provider)],
    vector_store: Annotated[VectorStore, Depends(get_vector_store)],
    language: Annotated[str, Form()] = "zh-CN",
    country_or_region: Annotated[str | None, Form()] = None,
    business_category: Annotated[str | None, Form()] = None,
) -> ApiResponse[IngestionJobData]:
    content = await file.read(settings.max_upload_bytes + 1)
    job = await KnowledgeService(session, settings, embedding, vector_store).upload_document(
        source_id=source_id,
        filename=file.filename or "document.txt",
        content=content,
        language=language,
        country_or_region=country_or_region,
        business_category=business_category,
    )
    return ApiResponse(request_id=request.state.request_id, data=IngestionJobData.model_validate(job))


@router.get("", response_model=ApiResponse[DocumentListData])
async def list_documents(
    request: Request,
    _: Annotated[User, Depends(require_roles("admin", "customer_service", "operator"))],
    session: Annotated[AsyncSession, Depends(get_session)],
    source_id: UUID | None = None,
) -> ApiResponse[DocumentListData]:
    documents = await KnowledgeRepository(session).list_documents(source_id=source_id)
    items = [DocumentData.model_validate(document) for document in documents]
    return ApiResponse(
        request_id=request.state.request_id,
        data=DocumentListData(items=items, count=len(items)),
    )


@router.get("/{document_id}", response_model=ApiResponse[DocumentData])
async def get_document(
    document_id: UUID,
    request: Request,
    _: Annotated[User, Depends(require_roles("admin", "customer_service", "operator"))],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ApiResponse[DocumentData]:
    document = await KnowledgeRepository(session).get_document(document_id)
    if document is None:
        raise NotFoundError("文档不存在")
    return ApiResponse(request_id=request.state.request_id, data=DocumentData.model_validate(document))


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: UUID,
    _: AdminUser,
    session: Annotated[AsyncSession, Depends(get_session)],
    vector_store: Annotated[VectorStore, Depends(get_vector_store)],
) -> None:
    document = await KnowledgeRepository(session).get_document(document_id)
    if document is None:
        raise NotFoundError("文档不存在")
    document.is_active = False
    await vector_store.delete_document(document.id)
    await session.commit()
