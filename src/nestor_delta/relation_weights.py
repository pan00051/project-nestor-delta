"""Layer-independent lagged relation weighting."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Mapping, Sequence, Tuple

NumericRow = Mapping[str, float]


@dataclass(frozen=True)
class RelationWeight:
    """Best lagged linear relation from one source variable to one target variable."""

    source: str
    target: str
    lag: int
    weight: float
    score: float
    sample_count: int
    transform: str = "none"
    stability: float | None = None
    uncertainty: float | None = None
    selected: bool | None = None


def compute_lagged_relation_weights(
    rows: Sequence[NumericRow],
    variables: Iterable[str],
    max_lag: int,
) -> List[RelationWeight]:
    """Compute directed relation weights for every ordered variable pair.

    The module is intentionally generic: it consumes named numeric histories and
    does not know about forecasting, business semantics, or data-layer targets.
    """
    variable_names = tuple(variables)
    if max_lag < 1:
        raise ValueError("max_lag must be at least 1")
    if len(rows) <= max_lag:
        raise ValueError("rows length must be greater than max_lag")
    if len(set(variable_names)) != len(variable_names):
        raise ValueError("variables must be unique")

    weights: List[RelationWeight] = []
    for target in variable_names:
        for source in variable_names:
            if source == target:
                continue
            weights.append(_best_weight_for_pair(rows, source, target, max_lag))

    return weights


def legacy_level_scoring(
    rows: Sequence[NumericRow],
    variables: Iterable[str],
    max_lag: int,
) -> List[RelationWeight]:
    """Run the frozen Sprint 2 level-Pearson scoring path."""
    return compute_lagged_relation_weights(rows, variables, max_lag)


def rank_target_sources(weights: Sequence[RelationWeight], target: str) -> List[RelationWeight]:
    """Return source weights for one target sorted by absolute strength."""
    return sorted(
        (weight for weight in weights if weight.target == target),
        key=lambda item: (-item.score, item.source),
    )


def _best_weight_for_pair(
    rows: Sequence[NumericRow], source: str, target: str, max_lag: int
) -> RelationWeight:
    best: RelationWeight | None = None
    for lag in range(1, max_lag + 1):
        source_values, target_values = _lagged_pair_values(rows, source, target, lag)
        coefficient = _pearson_correlation(source_values, target_values)
        candidate = RelationWeight(
            source=source,
            target=target,
            lag=lag,
            weight=coefficient,
            score=abs(coefficient),
            sample_count=len(source_values),
        )
        if best is None or candidate.score > best.score:
            best = candidate

    if best is None:
        raise ValueError("no relation weight could be computed")
    return best


def _lagged_pair_values(
    rows: Sequence[NumericRow], source: str, target: str, lag: int
) -> Tuple[List[float], List[float]]:
    source_values: List[float] = []
    target_values: List[float] = []
    for index in range(lag, len(rows)):
        source_values.append(float(rows[index - lag][source]))
        target_values.append(float(rows[index][target]))
    return source_values, target_values


def _pearson_correlation(left: Sequence[float], right: Sequence[float]) -> float:
    if len(left) != len(right):
        raise ValueError("left and right lengths differ")
    if not left:
        raise ValueError("cannot correlate empty sequences")

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

    denominator = (left_ss * right_ss) ** 0.5
    if denominator == 0.0:
        return 0.0
    return numerator / denominator
