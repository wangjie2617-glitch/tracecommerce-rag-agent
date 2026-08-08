"""Offline threshold calibration for evidence scores."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CalibrationPoint:
    score: float
    positive: bool


@dataclass(frozen=True, slots=True)
class ThresholdMetrics:
    threshold: float
    precision: float
    recall: float
    f1: float
    true_positive: int
    false_positive: int
    false_negative: int


def metrics_at_threshold(
    points: list[CalibrationPoint],
    threshold: float,
) -> ThresholdMetrics:
    true_positive = sum(point.positive and point.score >= threshold for point in points)
    false_positive = sum(not point.positive and point.score >= threshold for point in points)
    false_negative = sum(point.positive and point.score < threshold for point in points)
    precision = true_positive / (true_positive + false_positive) if true_positive + false_positive else 0.0
    recall = true_positive / (true_positive + false_negative) if true_positive + false_negative else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return ThresholdMetrics(
        threshold=round(threshold, 4),
        precision=round(precision, 4),
        recall=round(recall, 4),
        f1=round(f1, 4),
        true_positive=true_positive,
        false_positive=false_positive,
        false_negative=false_negative,
    )


def choose_threshold(
    points: list[CalibrationPoint],
    *,
    minimum_precision: float = 0.8,
) -> ThresholdMetrics:
    """Choose the best F1 threshold while preferring an evidence precision floor."""
    if not points:
        raise ValueError("至少需要一条校准样本")
    candidates = sorted({0.0, 1.0, *(point.score for point in points)})
    results = [metrics_at_threshold(points, threshold) for threshold in candidates]
    qualified = [result for result in results if result.precision >= minimum_precision]
    pool = qualified or results
    return max(pool, key=lambda result: (result.f1, result.precision, result.recall, result.threshold))
