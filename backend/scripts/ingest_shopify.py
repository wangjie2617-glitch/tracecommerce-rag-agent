"""Create and synchronize the approved Shopify Simplified Chinese source."""

from __future__ import annotations

import asyncio

from sqlalchemy import select

from app.config import get_settings
from app.db.models import KnowledgeSource
from app.db.session import SessionFactory
from app.dependencies import get_embedding_provider, get_vector_store
from app.schemas.knowledge import KnowledgeSourceCreate
from app.services.knowledge import KnowledgeService

SOURCE_NAME = "Shopify 官方中文帮助中心"


async def main() -> None:
    settings = get_settings()
    async with SessionFactory() as session:
        service = KnowledgeService(
            session,
            settings,
            get_embedding_provider(),
            get_vector_store(),
        )
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
                        "business_category": "cross_border_commerce",
                        "language": "zh-CN",
                        "start_urls": settings.shopify_allowed_prefixes,
                    },
                )
            )
        job = await service.sync_source(source.id)
        print(
            "Shopify 中文知识库导入完成："
            f"发现 {job.pages_discovered} 页，新增 {job.documents_created}，"
            f"更新 {job.documents_updated}，未变化 {job.documents_unchanged}，"
            f"写入 {job.chunks_written} 个 Chunk。"
        )


if __name__ == "__main__":
    asyncio.run(main())
