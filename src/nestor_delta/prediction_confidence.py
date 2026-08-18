"""S10 Prediction Confidence v0."""

from __future__ import annotations

from dataclasses import dataclass
from math import sqrt
from typing import Sequence, Tuple


@dataclass(frozen=True)
class PredictionConfidence:
    """Confidence components for one prediction."""

    relation_stability: float | None
    parameter_uncertainty: float | None
    input_support: float | None
    residual_uncertainty: float | None
    confidence: float | None


def compute_prediction_confidence(
    *,
    relation_stability: float | None,
    parameter_uncertainty: float | None,
    input_support: float | None,
    residual_uncertainty: float | None,
) -> PredictionConfidence:
    """Combine S10 confidence components into a nullable 0..1 score."""
    components = (
        relation_stability,
        _uncertainty_support(parameter_uncertainty),
        input_support,
        _uncertainty_support(residual_uncertainty),
    )
    if any(component is None for component in components):
        confidence = None
    else:
        averaged = sum(float(component) for component in components) / len(components)
        confidence = _clamp01(min(averaged, float(input_support)))
    return PredictionConfidence(
        relation_stability=relation_stability,
        parameter_uncertainty=parameter_uncertainty,
        input_support=input_support,
        residual_uncertainty=residual_uncertainty,
        confidence=confidence,
    )


def input_support_score(
    value: float,
    training_values: Sequence[float],
    *,
    margin_ratio: float = 0.25,
) -> float | None:
    """Return how far an input sits inside the train support envelope."""
    if not training_values:
        return None
    lower = min(training_values)
    upper = max(training_values)
    width = upper - lower
    if width == 0.0:
        return 1.0 if value == lower else 0.0
    margin = width * margin_ratio
    if lower <= value <= upper:
        return 1.0
    distance = lower - value if value < lower else value - upper
    return _clamp01(1.0 - distance / margin) if margin > 0.0 else 0.0


def calibration_bins(
    confidences: Sequence[float],
    errors: Sequence[float],
    *,
    bin_count: int = 4,
) -> Tuple[Tuple[float, float, int], ...]:
    """Return average confidence, average absolute error, and count per bin."""
    if len(confidences) != len(errors):
        raise ValueError("confidences and errors must have the same length")
    if bin_count < 1:
        raise ValueError("bin_count must be at least 1")
    rows = sorted(zip(confidences, errors), key=lambda item: item[0])
    if not rows:
        return ()
    output = []
    for bin_index in range(bin_count):
        start = bin_index * len(rows) // bin_count
        end = (bin_index + 1) * len(rows) // bin_count
        chunk = rows[start:end]
        if not chunk:
            continue
        output.append(
            (
                sum(confidence for confidence, _ in chunk) / len(chunk),
                sum(abs(error) for _, error in chunk) / len(chunk),
                len(chunk),
            )
        )
    return tuple(output)


def spearman_rank_correlation(left: Sequence[float], right: Sequence[float]) -> float:
    """Spearman rank correlation with average ranks for ties."""
    if len(left) != len(right):
        raise ValueError("left and right must have the same length")
    if len(left) < 2:
        raise ValueError("rank correlation requires at least two observations")
    return _pearson(_average_ranks(left), _average_ranks(right))


def _uncertainty_support(value: float | None) -> float | None:
    if value is None:
        return None
    if value < 0.0:
        raise ValueError("uncertainty values must be non-negative")
    return 1.0 / (1.0 + value)


def _average_ranks(values: Sequence[float]) -> Tuple[float, ...]:
    indexed = sorted(enumerate(values), key=lambda item: item[1])
    ranks = [0.0 for _ in values]
    index = 0
    while index < len(indexed):
        end = index + 1
        while end < len(indexed) and indexed[end][1] == indexed[index][1]:
            end += 1
        rank = (index + 1 + end) / 2.0
        for original_index, _ in indexed[index:end]:
            ranks[original_index] = rank
        index = end
    return tuple(ranks)


def _pearson(left: Sequence[float], right: Sequence[float]) -> float:
    left_mean = sum(left) / len(left)
    right_mean = sum(right) / len(right)
    numerator = 0.0
    left_ss = 0.0
    right_ss = 0.0
    for left_value, right_value in zip(left, right):
        left_delta = left_value - left_mean
        right_delta = right_value - right_mean
        numerator += left_delta * right_delta
        left_ss += left_delta * left_delta
        right_ss += right_delta * right_delta
    denominator = sqrt(left_ss * right_ss)
    if denominator == 0.0:
        return 0.0
    return numerator / denominator


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))
