"""Structure-aware chunking tests."""

from app.rag.chunker import StructureAwareChunker


def test_chunker_preserves_sections_and_size() -> None:
    text = """
# Duties and taxes

Merchants can collect duties and import taxes at checkout.

The tax responsibility depends on the destination.

## Refunds

Refunds can be full or partial.
"""
    chunks = StructureAwareChunker(max_chars=200, overlap_chars=20).split(text)
    assert chunks
    assert chunks[0].section_title == "Duties and taxes"
    assert any(chunk.section_title == "Refunds" for chunk in chunks)
    assert all(len(chunk.content) <= 220 for chunk in chunks)
    assert all(len(chunk.content_hash) == 64 for chunk in chunks)


def test_chunker_rejects_invalid_overlap() -> None:
    try:
        StructureAwareChunker(max_chars=200, overlap_chars=200)
    except ValueError as exc:
        assert "overlap_chars" in str(exc)
    else:
        raise AssertionError("Expected ValueError")

