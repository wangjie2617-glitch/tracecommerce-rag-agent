"""Chinese-first text normalization and lexical tokenization for retrieval."""

from __future__ import annotations

import re
import unicodedata

_LATIN_TOKEN = re.compile(r"[a-z0-9_]+")
_CJK_SPAN = re.compile(r"[\u4e00-\u9fff]+")

# Normalize common customer expressions to the terminology used by the knowledge base.
_QUERY_ALIASES = (
    ("退钱", "退款"),
    ("退货退款", "退货 退款"),
    ("快递", "物流 配送"),
    ("包裹", "物流包裹"),
    ("税钱", "税费"),
    ("进口税费", "关税 进口税"),
    ("海关税", "关税"),
    ("换钱", "货币兑换"),
    ("外币", "本地货币"),
    ("登录不上", "无法登录 账户"),
)


def normalize_query(text: str) -> str:
    """Normalize Unicode, whitespace, casing, and common Chinese business aliases."""
    normalized = unicodedata.normalize("NFKC", text).lower()
    normalized = " ".join(normalized.split())
    for source, target in _QUERY_ALIASES:
        normalized = normalized.replace(source, target)
    return normalized


def tokenize_for_retrieval(text: str) -> list[str]:
    """Tokenize mixed Chinese/English text without requiring a dictionary package.

    Chinese spans are represented by character bi-grams and tri-grams. Single
    characters are retained only for one-character spans, which reduces noise
    from common words while preserving terms such as “税”.
    """
    normalized = normalize_query(text)
    tokens = _LATIN_TOKEN.findall(normalized)
    for span in _CJK_SPAN.findall(normalized):
        if len(span) == 1:
            tokens.append(span)
            continue
        tokens.extend(span[index : index + 2] for index in range(len(span) - 1))
        if len(span) >= 3:
            tokens.extend(span[index : index + 3] for index in range(len(span) - 2))
    return tokens
