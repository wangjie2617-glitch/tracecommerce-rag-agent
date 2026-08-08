"""Query rewriting, metadata filter, citation, and evidence unit tests."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.rag.citation import build_citations, verify_citations
from app.rag.evaluator import EvidenceEvaluator
from app.rag.llm import FakeLLM
from app.rag.tokenization import normalize_query, tokenize_for_retrieval
from app.rag.types import RetrievedDocument
from app.vectorstores.milvus_store import MilvusVectorStore


def _document(score: float = 0.8, rerank: float | None = 0.9) -> RetrievedDocument:
    return RetrievedDocument(
        chunk_id=uuid4(),
        document_id=uuid4(),
        source_id=uuid4(),
        company_name="Shopify",
        source_type="website",
        title="关税和进口税",
        section_title="概览",
        source_url="https://help.shopify.com/zh-CN/manual/international/duties-and-import-taxes",
        content="跨境订单需要填写 HS 编码和原产地信息，以便计算关税和进口税。",
        language="zh-CN",
        country_or_region=None,
        business_category="duties_and_taxes",
        version=1,
        is_active=True,
        crawled_at=datetime.now(UTC),
        retrieval_score=score,
        rerank_score=rerank,
    )


@pytest.mark.asyncio
async def test_fake_llm_query_rewrite() -> None:
    llm = FakeLLM()
    assert await llm.rewrite_query("  Shopify   退钱  ", language="zh-CN", retry_count=0) == "shopify 退款"
    retry = await llm.rewrite_query("Shopify 关税", language="zh-CN", retry_count=1)
    assert retry.endswith("Shopify 官方帮助")


def test_chinese_retrieval_tokenization_and_aliases() -> None:
    assert normalize_query("客户想退钱") == "客户想退款"
    query_tokens = set(tokenize_for_retrieval("国际订单怎么退钱"))
    document_tokens = set(tokenize_for_retrieval("订单退款处理规则"))
    assert "退款" in query_tokens
    assert query_tokens & document_tokens


def test_metadata_filter_is_allowlisted_and_escaped() -> None:
    expression = MilvusVectorStore.build_filter_expression(
        {
            "company_name": 'Shop"ify',
            "language": ["en", "zh-CN"],
            "unsupported": "ignored",
            "is_active": True,
        }
    )
    assert "is_active == true" in expression
    assert 'company_name in ["Shop\\"ify"]' in expression
    assert 'language in ["en", "zh-CN"]' in expression
    assert "unsupported" not in expression


def test_citations_are_copied_and_verified() -> None:
    document = _document()
    citations = build_citations([document])
    assert citations[0]["quoted_text"] in document.content
    assert verify_citations(citations, [document])
    citations[0]["quoted_text"] = "fabricated text"
    assert not verify_citations(citations, [document])


def test_evidence_sufficiency() -> None:
    score, sufficient = EvidenceEvaluator(0.45).evaluate([_document()])
    assert score >= 0.45
    assert sufficient
    assert EvidenceEvaluator(0.45).evaluate([]) == (0.0, False)
