"""Evidence level and threshold calibration tests."""

from app.rag.calibration import CalibrationPoint, choose_threshold, metrics_at_threshold
from app.rag.evaluator import classify_evidence_level


def test_evidence_levels_are_explicitly_non_probabilistic() -> None:
    assert classify_evidence_level(0.9, False) == "insufficient"
    assert classify_evidence_level(0.2, True) == "low"
    assert classify_evidence_level(0.5, True) == "medium"
    assert classify_evidence_level(0.8, True) == "high"


def test_threshold_metrics() -> None:
    points = [
        CalibrationPoint(0.9, True),
        CalibrationPoint(0.7, True),
        CalibrationPoint(0.6, False),
        CalibrationPoint(0.2, False),
    ]
    metrics = metrics_at_threshold(points, 0.7)
    assert metrics.precision == 1.0
    assert metrics.recall == 1.0
    assert metrics.f1 == 1.0


def test_choose_threshold_respects_precision_floor() -> None:
    points = [
        CalibrationPoint(0.9, True),
        CalibrationPoint(0.7, True),
        CalibrationPoint(0.65, False),
        CalibrationPoint(0.3, True),
        CalibrationPoint(0.2, False),
    ]
    result = choose_threshold(points, minimum_precision=0.8)
    assert result.threshold == 0.7
    assert result.precision == 1.0
