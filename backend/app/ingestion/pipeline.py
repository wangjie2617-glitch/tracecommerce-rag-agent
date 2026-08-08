"""End-to-end document versioning, chunking, embedding, and vector persistence."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import IngestionJob, KnowledgeSource
from app.rag.chunker import StructureAwareChunker
from app.rag.embeddings import EmbeddingProvider
from app.rag.types import ChunkRecord, ParsedDocument
from app.repositories.knowledge import KnowledgeRepository
from app.vectorstores.base import VectorStore


class IngestionPipeline:
    """Persist only changed content and keep PostgreSQL/Milvus metadata aligned."""

    def __init__(
        self,
        session: AsyncSession,
        embedding: EmbeddingProvider,
        vector_store: VectorStore,
        *,
        chunker: StructureAwareChunker | None = None,
    ) -> None:
        self.session = session
        self.embedding = embedding
        self.vector_store = vector_store
        self.chunker = chunker or StructureAwareChunker()
        self.repository = KnowledgeRepository(session)

    async def ingest(
        self,
        source: KnowledgeSource,
        parsed_documents: list[ParsedDocument],
        *,
        job: IngestionJob | None = None,
        force_reindex: bool = False,
    ) -> IngestionJob:
        """Ingest parsed documents and update an ingestion job atomically per document."""
        active_job = job or await self.repository.create_job(source.id)
        active_job.pages_discovered = len(parsed_documents)
        await self.vector_store.ensure_collection(self.embedding.dimension)
        try:
            for parsed in parsed_documents:
                content_hash = hashlib.sha256(parsed.content.encode("utf-8")).hexdigest()
                document, status = await self.repository.save_document(
                    source_id=source.id,
                    parsed=parsed,
                    content_hash=content_hash,
                )
                if status == "unchanged" and not force_reindex:
                    active_job.documents_unchanged += 1
                    await self.session.commit()
                    continue
                pieces = self.chunker.split(parsed.content)
                vectors = await self.embedding.embed_documents([piece.content for piece in pieces])
                chunks: list[ChunkRecord] = []
                for piece, vector in zip(pieces, vectors, strict=True):
                    chunk_id = uuid4()
                    chunks.append(
                        ChunkRecord(
                            id=str(chunk_id),
                            chunk_id=chunk_id,
                            document_id=document.id,
                            source_id=source.id,
                            company_name=source.company_name,
                            source_type=parsed.source_type,
                            title=parsed.title,
                            section_title=piece.section_title,
                            source_url=parsed.source_url,
                            content=piece.content,
                            language=parsed.language,
                            country_or_region=parsed.country_or_region,
                            business_category=parsed.business_category,
                            published_at=parsed.published_at,
                            crawled_at=parsed.crawled_at,
                            content_hash=piece.content_hash,
                            version=document.current_version,
                            dense_vector=vector,
                        )
                    )
                if status in {"updated", "unchanged"}:
                    await self.vector_store.delete_document(document.id)
                if status == "updated":
                    active_job.documents_updated += 1
                elif status == "created":
                    active_job.documents_created += 1
                else:
                    active_job.documents_unchanged += 1
                await self.vector_store.upsert(chunks)
                active_job.chunks_written += len(chunks)
                await self.session.commit()
            active_job.status = "completed"
            active_job.finished_at = datetime.now(UTC)
            source.last_synced_at = active_job.finished_at
            await self.session.commit()
            return active_job
        except Exception as exc:
            await self.session.rollback()
            active_job.status = "failed"
            active_job.error = str(exc)[:4000]
            active_job.finished_at = datetime.now(UTC)
            self.session.add(active_job)
            await self.session.commit()
            raise
