"""Knowledge source, document version, and ingestion job persistence."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Document, DocumentVersion, IngestionJob, KnowledgeSource
from app.rag.types import ParsedDocument


class KnowledgeRepository:
    """Store source configuration and versioned document metadata."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_source(
        self,
        *,
        name: str,
        company_name: str,
        source_type: str,
        base_url: str | None,
        config: dict,
    ) -> KnowledgeSource:
        source = KnowledgeSource(
            name=name,
            company_name=company_name,
            source_type=source_type,
            base_url=base_url,
            config=config,
        )
        self.session.add(source)
        await self.session.flush()
        return source

    async def get_source(self, source_id: UUID) -> KnowledgeSource | None:
        result = await self.session.execute(
            select(KnowledgeSource).where(KnowledgeSource.id == source_id)
        )
        return result.scalar_one_or_none()

    async def list_sources(self) -> list[KnowledgeSource]:
        result = await self.session.execute(
            select(KnowledgeSource).order_by(KnowledgeSource.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_document(self, document_id: UUID) -> Document | None:
        result = await self.session.execute(select(Document).where(Document.id == document_id))
        return result.scalar_one_or_none()

    async def get_document_by_url(self, source_id: UUID, source_url: str) -> Document | None:
        result = await self.session.execute(
            select(Document).where(
                Document.source_id == source_id,
                Document.source_url == source_url,
            )
        )
        return result.scalar_one_or_none()

    async def list_documents(self, *, source_id: UUID | None = None) -> list[Document]:
        statement = select(Document)
        if source_id is not None:
            statement = statement.where(Document.source_id == source_id)
        result = await self.session.execute(statement.order_by(Document.created_at.desc()))
        return list(result.scalars().all())

    async def save_document(
        self,
        *,
        source_id: UUID,
        parsed: ParsedDocument,
        content_hash: str,
    ) -> tuple[Document, str]:
        document = await self.get_document_by_url(source_id, parsed.source_url)
        if document is not None and document.content_hash == content_hash:
            document.crawled_at = parsed.crawled_at
            return document, "unchanged"
        if document is None:
            document = Document(
                source_id=source_id,
                title=parsed.title,
                source_url=parsed.source_url,
                source_type=parsed.source_type,
                language=parsed.language,
                country_or_region=parsed.country_or_region,
                business_category=parsed.business_category,
                published_at=parsed.published_at,
                crawled_at=parsed.crawled_at,
                content_hash=content_hash,
                current_version=1,
            )
            self.session.add(document)
            status = "created"
        else:
            document.title = parsed.title
            document.language = parsed.language
            document.country_or_region = parsed.country_or_region
            document.business_category = parsed.business_category
            document.published_at = parsed.published_at
            document.crawled_at = parsed.crawled_at
            document.content_hash = content_hash
            document.current_version += 1
            document.is_active = True
            status = "updated"
        await self.session.flush()
        self.session.add(
            DocumentVersion(
                document_id=document.id,
                version=document.current_version,
                raw_content=parsed.content,
                content_hash=content_hash,
                crawled_at=parsed.crawled_at,
                metadata_json={
                    "title": parsed.title,
                    "source_url": parsed.source_url,
                    "language": parsed.language,
                    "country_or_region": parsed.country_or_region,
                    "business_category": parsed.business_category,
                },
            )
        )
        await self.session.flush()
        return document, status

    async def create_job(self, source_id: UUID | None) -> IngestionJob:
        job = IngestionJob(source_id=source_id, status="running", started_at=datetime.now(UTC))
        self.session.add(job)
        await self.session.flush()
        return job

    async def get_job(self, job_id: UUID) -> IngestionJob | None:
        result = await self.session.execute(select(IngestionJob).where(IngestionJob.id == job_id))
        return result.scalar_one_or_none()

    async def list_jobs(self, source_id: UUID | None = None) -> list[IngestionJob]:
        statement = select(IngestionJob)
        if source_id is not None:
            statement = statement.where(IngestionJob.source_id == source_id)
        result = await self.session.execute(statement.order_by(IngestionJob.created_at.desc()))
        return list(result.scalars().all())
