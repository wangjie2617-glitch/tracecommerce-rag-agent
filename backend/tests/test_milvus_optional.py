"""Optional real-Milvus integration check, disabled unless explicitly configured."""

import os

import pytest

from app.vectorstores.milvus_store import MilvusVectorStore


@pytest.mark.milvus
@pytest.mark.asyncio
async def test_real_milvus_health_when_configured() -> None:
    uri = os.getenv("MILVUS_TEST_URI")
    if not uri:
        pytest.skip("Set MILVUS_TEST_URI to run the real Milvus integration test")
    store = MilvusVectorStore(uri, "tracecommerce_test_chunks")
    assert await store.health()
