"""LangGraph happy path, fallback, branch, and retry tests."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.agents.graph import build_agent_graph
from app.agents.nodes.core import FALLBACK_ANSWER, AgentNodes
from app.rag.embeddings import FakeEmbedding
from app.rag.evaluator import EvidenceEvaluator
from app.rag.llm import FakeLLM
from app.rag.reranker import MockReranker
from app.rag.retriever import HybridRetriever
from app.rag.types import ChunkRecord
from app.vectorstores.memory import InMemoryVectorStore


async def _graph_with_store(has_document: bool):
    embedding = FakeEmbedding(64)
    store = InMemoryVectorStore()
    await store.ensure_collection(64)
    if has_document:
        content = "跨境订单需要填写商品的 HS 编码和原产国家或地区，以便计算关税和进口税。"
        vector = await embedding.embed_query(content)
        identifier = uuid4()
        await store.upsert(
            [
                ChunkRecord(
                    id=str(identifier),
                    chunk_id=identifier,
                    document_id=uuid4(),
                    source_id=uuid4(),
                    company_name="Shopify",
                    source_type="website",
                    title="关税和进口税",
                    section_title="跨境订单要求",
                    source_url="https://help.shopify.com/zh-CN/manual/international/duties-and-import-taxes",
                    content=content,
                    language="zh-CN",
                    business_category="duties_and_taxes",
                    crawled_at=datetime.now(UTC),
                    content_hash="a" * 64,
                    version=1,
                    dense_vector=vector,
                )
            ]
        )
    nodes = AgentNodes(
        llm=FakeLLM(),
        retriever=HybridRetriever(embedding, store, minimum_score=0.0),
        reranker=MockReranker(),
        evaluator=EvidenceEvaluator(0.0),
        retrieval_top_k=5,
        rerank_top_k=3,
    )
    return build_agent_graph(nodes)


def _state(query: str) -> dict:
    return {
        "request_id": str(uuid4()),
        "thread_id": str(uuid4()),
        "user_id": str(uuid4()),
        "role": "operator",
        "original_query": query,
        "filters": {},
        "execution_trace": [],
        "warnings": [],
        "risk_flags": [],
        "retry_count": 0,
        "error": None,
    }


@pytest.mark.asyncio
async def test_graph_returns_grounded_answer_with_real_citation() -> None:
    graph = await _graph_with_store(True)
    state = _state("Shopify 跨境订单为什么需要填写 HS 编码？")
    result = await graph.ainvoke(
        state,
        config={"configurable": {"thread_id": state["thread_id"]}},
    )
    assert result["grounded"] is True
    assert result["evidence_score"] >= 0.0
    assert result["evidence_level"] in {"low", "medium", "high"}
    assert result["citations"]
    assert result["language"] == "zh-CN"
    assert result["filters"]["language"] == "zh-CN"
    assert result["citations"][0]["quoted_text"] in result["reranked_documents"][0]["content"]
    nodes = [item["node"] for item in result["execution_trace"]]
    assert "retrieve_documents" in nodes
    assert "verify_citations" in nodes


@pytest.mark.asyncio
async def test_graph_out_of_scope_falls_back() -> None:
    graph = await _graph_with_store(True)
    state = _state("请帮我写一首关于春天的诗")
    result = await graph.ainvoke(
        state,
        config={"configurable": {"thread_id": state["thread_id"]}},
    )
    assert result["answer"] == FALLBACK_ANSWER
    assert result["grounded"] is False
    assert result["evidence_score"] == 0.0
    assert result["evidence_level"] == "insufficient"
    assert result["intent"] == "out_of_scope"


@pytest.mark.asyncio
async def test_graph_empty_retrieval_retries_twice_then_falls_back() -> None:
    graph = await _graph_with_store(False)
    state = _state("Shopify shipping to Mars")
    result = await graph.ainvoke(
        state,
        config={"configurable": {"thread_id": state["thread_id"]}},
    )
    retrieval_steps = [
        item for item in result["execution_trace"] if item["node"] == "retrieve_documents"
    ]
    assert len(retrieval_steps) == 3
    assert result["answer"] == FALLBACK_ANSWER
    assert result["evidence_level"] == "insufficient"
