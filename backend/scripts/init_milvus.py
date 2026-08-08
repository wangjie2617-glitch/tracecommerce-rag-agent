"""Create the Milvus collection using the configured embedding dimension."""

from __future__ import annotations

import asyncio

from app.dependencies import get_embedding_provider, get_vector_store


async def main() -> None:
    embedding = get_embedding_provider()
    vector_store = get_vector_store()
    await vector_store.ensure_collection(embedding.dimension)
    if not await vector_store.health():
        raise RuntimeError("Milvus 健康检查失败")
    print(f"Milvus Collection 已就绪，向量维度: {embedding.dimension}")


if __name__ == "__main__":
    asyncio.run(main())

