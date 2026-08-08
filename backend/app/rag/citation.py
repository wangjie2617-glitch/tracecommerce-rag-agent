"""Build and verify citations only from retrieved source chunks."""

from __future__ import annotations

from typing import Any

from app.rag.types import RetrievedDocument


def build_citations(documents: list[RetrievedDocument], *, limit: int = 3) -> list[dict[str, Any]]:
    """Create traceable citations; quoted text is copied from the Chunk."""
    citations: list[dict[str, Any]] = []
    for document in documents[:limit]:
        quoted_text = " ".join(document.content.split())[:700]
        citations.append(
            {
                "document_id": str(document.document_id),
                "chunk_id": str(document.chunk_id),
                "title": document.title,
                "section_title": document.section_title,
                "source_url": document.source_url,
                "quoted_text": quoted_text,
                "retrieval_score": document.retrieval_score,
                "rerank_score": document.rerank_score,
                "crawled_at": document.crawled_at.isoformat(),
            }
        )
    return citations


def verify_citations(
    citations: list[dict[str, Any]],
    documents: list[RetrievedDocument],
) -> bool:
    """Require every quoted fragment and URL to match an actual retrieved Chunk."""
    by_chunk = {str(document.chunk_id): document for document in documents}
    if not citations:
        return False
    for citation in citations:
        document = by_chunk.get(str(citation.get("chunk_id")))
        if document is None:
            return False
        quote = str(citation.get("quoted_text", ""))
        normalized_content = " ".join(document.content.split())
        if not quote or quote not in normalized_content:
            return False
        if citation.get("source_url") != document.source_url:
            return False
    return True

