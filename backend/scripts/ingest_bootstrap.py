"""Ingest bundled Chinese Shopify Help Center summaries."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from sqlalchemy import select

from app.config import get_settings
from app.db.models import KnowledgeSource
from app.db.session import SessionFactory
from app.dependencies import get_embedding_provider, get_vector_store
from app.ingestion.pipeline import IngestionPipeline
from app.rag.types import ParsedDocument
from app.schemas.knowledge import KnowledgeSourceCreate
from app.services.knowledge import KnowledgeService

SOURCE_NAME = "Shopify 官方中文知识库"


async def main() -> None:
    settings = get_settings()
    data_path = Path(__file__).resolve().parents[1] / "data" / "shopify_bootstrap.json"
    records = json.loads(data_path.read_text(encoding="utf-8"))
    documents = [ParsedDocument.model_validate(record) for record in records]
    async with SessionFactory() as session:
        embedding = get_embedding_provider()
        vector_store = get_vector_store()
        service = KnowledgeService(session, settings, embedding, vector_store)
        result = await session.execute(
            select(KnowledgeSource).where(KnowledgeSource.name == SOURCE_NAME)
        )
        source = result.scalar_one_or_none()
        if source is None:
            source = await service.create_source(
                KnowledgeSourceCreate(
                    name=SOURCE_NAME,
                    company_name="Shopify",
                    source_type="website",
                    base_url="https://help.shopify.com/zh-CN/manual/international",
                    config={
                        "dataset": "Shopify 官方简体中文帮助中心摘要",
                        "language": "zh-CN",
                        "business_category": "cross_border_commerce",
                    },
                )
            )
        job = await IngestionPipeline(
            session,
            embedding,
            vector_store,
        ).ingest(source, documents, force_reindex=True)
        print(
            "中文启动数据导入完成："
            f"新增 {job.documents_created} 篇，"
            f"更新 {job.documents_updated} 篇，"
            f"写入 {job.chunks_written} 个 Chunk。"
        )


if __name__ == "__main__":
    asyncio.run(main())
