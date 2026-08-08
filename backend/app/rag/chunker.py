"""Structure-aware chunking that preserves headings, paragraphs, and lists."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass


@dataclass(frozen=True)
class TextChunk:
    section_title: str | None
    content: str
    content_hash: str


class StructureAwareChunker:
    """Group logical blocks under headings before applying a size limit."""

    def __init__(self, *, max_chars: int = 1200, overlap_chars: int = 120) -> None:
        if max_chars < 200:
            raise ValueError("max_chars 不能小于 200")
        if overlap_chars < 0 or overlap_chars >= max_chars:
            raise ValueError("overlap_chars 必须大于等于 0 且小于 max_chars")
        self.max_chars = max_chars
        self.overlap_chars = overlap_chars

    @staticmethod
    def _logical_blocks(text: str) -> list[tuple[str | None, str]]:
        section: str | None = None
        blocks: list[tuple[str | None, str]] = []
        for raw in re.split(r"\n\s*\n", text):
            value = " ".join(raw.strip().split())
            if not value:
                continue
            heading = re.match(r"^#{1,6}\s+(.+)$", value)
            if heading:
                section = heading.group(1).strip()
                continue
            blocks.append((section, value))
        return blocks

    def split(self, text: str) -> list[TextChunk]:
        """Split text without breaking short paragraphs or losing section names."""
        chunks: list[TextChunk] = []
        current_section: str | None = None
        current: list[str] = []
        current_length = 0

        def flush() -> None:
            nonlocal current, current_length
            if not current:
                return
            content = "\n\n".join(current).strip()
            chunks.append(
                TextChunk(
                    section_title=current_section,
                    content=content,
                    content_hash=hashlib.sha256(content.encode("utf-8")).hexdigest(),
                )
            )
            overlap = content[-self.overlap_chars :].strip() if self.overlap_chars else ""
            current = [overlap] if overlap else []
            current_length = len(overlap)

        for section, block in self._logical_blocks(text):
            if section != current_section and current:
                flush()
                current = []
                current_length = 0
            current_section = section
            if len(block) > self.max_chars:
                sentences = re.split(r"(?<=[。！？.!?])\s+", block)
            else:
                sentences = [block]
            for sentence in sentences:
                if current and current_length + len(sentence) + 2 > self.max_chars:
                    flush()
                current.append(sentence)
                current_length += len(sentence) + 2
        flush()
        return chunks

