"""Document ingestion, versioning, and vector insertion integration tests."""

from datetime import UTC, datetime

import pytest

from app.db.models import KnowledgeSource
from app.ingestion.pipeline import IngestionPipeline
from app.rag.embeddings import FakeEmbedding
from app.rag.types import ParsedDocument
from app.repositories.knowledge import KnowledgeRepository
from app.vectorstores.memory import InMemoryVectorStore


@pytest.mark.asyncio
async def test_document_ingestion_and_unchanged_skip(session) -> None:
    source = KnowledgeSource(
        name="Shopify Help",
        company_name="Shopify",
        source_type="website",
        base_url="https://help.shopify.com/en/manual/international",
        config={},
    )
    session.add(source)
    await session.commit()
    parsed = ParsedDocument(
        title="International sales tools",
        source_url="https://help.shopify.com/en/manual/international",
        source_type="website",
        content="# International sales tools\n\nShopify helps merchants manage international markets.",
        language="en",
        business_category="international_market",
        crawled_at=datetime.now(UTC),
    )
    store = InMemoryVectorStore()
    pipeline = IngestionPipeline(session, FakeEmbedding(64), store)
    first = await pipeline.ingest(source, [parsed])
    assert first.status == "completed"
    assert first.documents_created == 1
    assert first.chunks_written >= 1

    second = await pipeline.ingest(source, [parsed])
    assert second.documents_unchanged == 1
    documents = await KnowledgeRepository(session).list_documents(source_id=source.id)
    assert len(documents) == 1
    assert documents[0].current_version == 1


@pytest.mark.asyncio
async def test_document_change_creates_new_version(session) -> None:
    source = KnowledgeSource(
        name="Shopify Help",
        company_name="Shopify",
        source_type="website",
        base_url="https://help.shopify.com/en/manual/taxes",
        config={},
    )
    session.add(source)
    await session.commit()
    base = {
        "title": "Taxes",
        "source_url": "https://help.shopify.com/en/manual/taxes",
        "source_type": "website",
        "language": "en",
        "crawled_at": datetime.now(UTC),
    }
    pipeline = IngestionPipeline(session, FakeEmbedding(32), InMemoryVectorStore())
    await pipeline.ingest(source, [ParsedDocument(content="Tax rules version one.", **base)])
    await pipeline.ingest(source, [ParsedDocument(content="Tax rules version two.", **base)])
    document = (await KnowledgeRepository(session).list_documents(source_id=source.id))[0]
    assert document.current_version == 2


@pytest.mark.asyncio
async def test_force_reindex_rebuilds_vectors_without_new_version(session) -> None:
    source = KnowledgeSource(
        name="Shopify Bootstrap",
        company_name="Shopify",
        source_type="website",
        base_url="https://help.shopify.com/en/manual/markets",
        config={},
    )
    session.add(source)
    await session.commit()
    parsed = ParsedDocument(
        title="Markets",
        source_url="https://help.shopify.com/en/manual/markets",
        source_type="website",
        content="Shopify Markets helps manage international sales.",
        language="en",
        crawled_at=datetime.now(UTC),
    )
    store = InMemoryVectorStore()
    pipeline = IngestionPipeline(session, FakeEmbedding(32), store)
    await pipeline.ingest(source, [parsed])
    rebuilt = await pipeline.ingest(source, [parsed], force_reindex=True)
    assert rebuilt.documents_unchanged == 1
    assert rebuilt.chunks_written == 1
    documents = await KnowledgeRepository(session).list_documents(source_id=source.id)
    assert documents[0].current_version == 1
