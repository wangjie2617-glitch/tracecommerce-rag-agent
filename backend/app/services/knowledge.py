"""Knowledge source CRUD, controlled crawling, and local document ingestion."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.core.exceptions import AppError, NotFoundError
from app.ingestion.crawler import CrawlPolicy, SafeWebCrawler
from app.ingestion.loaders import load_local_document
from app.ingestion.pipeline import IngestionPipeline
from app.rag.embeddings import EmbeddingProvider
from app.rag.types import ParsedDocument
from app.repositories.knowledge import KnowledgeRepository
from app.schemas.knowledge import KnowledgeSourceCreate, KnowledgeSourceUpdate
from app.vectorstores.base import VectorStore


class KnowledgeService:
    """Business-facing knowledge source and document operations."""

    def __init__(
        self,
        session: AsyncSession,
        settings: Settings,
        embedding: EmbeddingProvider,
        vector_store: VectorStore,
    ) -> None:
        self.session = session
        self.settings = settings
        self.embedding = embedding
        self.vector_store = vector_store
        self.repository = KnowledgeRepository(session)

    async def create_source(self, payload: KnowledgeSourceCreate):
        source = await self.repository.create_source(
            name=payload.name,
            company_name=payload.company_name,
            source_type=payload.source_type,
            base_url=str(payload.base_url) if payload.base_url else None,
            config=payload.config,
        )
        await self.session.commit()
        return source

    async def get_source(self, source_id: UUID):
        source = await self.repository.get_source(source_id)
        if source is None:
            raise NotFoundError("知识源不存在")
        return source

    async def list_sources(self):
        return await self.repository.list_sources()

    async def get_job(self, job_id: UUID):
        job = await self.repository.get_job(job_id)
        if job is None:
            raise NotFoundError("同步任务不存在")
        return job

    async def list_jobs(self, source_id: UUID | None = None):
        return await self.repository.list_jobs(source_id)

    async def update_source(self, source_id: UUID, payload: KnowledgeSourceUpdate):
        source = await self.get_source(source_id)
        updates = payload.model_dump(exclude_unset=True)
        if "base_url" in updates and updates["base_url"] is not None:
            updates["base_url"] = str(updates["base_url"])
        for key, value in updates.items():
            setattr(source, key, value)
        await self.session.commit()
        return source

    async def disable_source(self, source_id: UUID) -> None:
        source = await self.get_source(source_id)
        source.is_active = False
        await self.session.commit()

    async def sync_source(self, source_id: UUID):
        source = await self.get_source(source_id)
        if not source.is_active:
            raise AppError("知识源已停用", code="source_inactive", status_code=409)
        if source.source_type != "website" or not source.base_url:
            raise AppError("只有 website 知识源支持网页同步", code="invalid_source_type", status_code=409)
        configured_urls = source.config.get("start_urls") if isinstance(source.config, dict) else None
        start_urls = configured_urls or [source.base_url]
        policy = CrawlPolicy(
            allowed_prefixes=tuple(self.settings.shopify_allowed_prefixes),
            user_agent=self.settings.crawler_user_agent,
            timeout_seconds=self.settings.crawler_timeout_seconds,
            delay_seconds=max(self.settings.crawler_delay_seconds, 1.0),
            max_pages=self.settings.crawler_max_pages,
            max_depth=self.settings.crawler_max_depth,
        )
        pages = await SafeWebCrawler(policy).crawl([str(url) for url in start_urls])
        source_language = (
            source.config.get("language", "zh-CN")
            if isinstance(source.config, dict)
            else "zh-CN"
        )
        parsed = [
            ParsedDocument(
                title=page.title,
                source_url=page.url,
                source_type="website",
                content=page.content,
                language=source_language,
                business_category=source.config.get("business_category"),
                published_at=page.published_at,
                crawled_at=page.crawled_at,
            )
            for page in pages
        ]
        return await IngestionPipeline(
            self.session,
            self.embedding,
            self.vector_store,
        ).ingest(source, parsed)

    async def upload_document(
        self,
        *,
        source_id: UUID,
        filename: str,
        content: bytes,
        language: str,
        country_or_region: str | None,
        business_category: str | None,
    ):
        source = await self.get_source(source_id)
        if len(content) > self.settings.max_upload_bytes:
            raise AppError("上传文件超过大小限制", code="file_too_large", status_code=413)
        parsed = await load_local_document(
            filename=filename,
            content=content,
            source_url=f"upload://{source_id}/{filename}",
            language=language,
            country_or_region=country_or_region,
            business_category=business_category,
        )
        return await IngestionPipeline(
            self.session,
            self.embedding,
            self.vector_store,
        ).ingest(source, [parsed])
