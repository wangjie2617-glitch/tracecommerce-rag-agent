"""Evidence sufficiency scoring."""

from __future__ import annotations

from typing import Literal

from app.rag.types import RetrievedDocument

EvidenceLevel = Literal["insufficient", "low", "medium", "high"]


def classify_evidence_level(score: float, sufficient: bool) -> EvidenceLevel:
    """Convert the raw evidence score into an honest, non-probabilistic band."""
    if not sufficient:
        return "insufficient"
    if score >= 0.65:
        return "high"
    if score >= 0.35:
        return "medium"
    return "low"


class EvidenceEvaluator:
    """Calculate a conservative score from the best reranked chunks."""

    def __init__(self, threshold: float = 0.45) -> None:
        self.threshold = threshold

    def evaluate(self, documents: list[RetrievedDocument]) -> tuple[float, bool]:
        if not documents:
            return 0.0, False
        scores = [
            document.rerank_score
            if document.rerank_score is not None
            else document.retrieval_score
            for document in documents[:3]
        ]
        top_score = max(scores)
        mean_score = sum(scores) / len(scores)
        evidence_score = round(0.7 * top_score + 0.3 * mean_score, 4)
        return evidence_score, evidence_score >= self.threshold
