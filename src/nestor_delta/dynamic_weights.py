"""Causal rolling updates around the frozen static relation-weight mechanism."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Sequence, Tuple

from .relation_weights import (
    NumericRow,
    compute_lagged_relation_weights,
)


@dataclass(frozen=True)
class TimedRelationWeight:
    """One static relation estimate attached to its causal rolling window."""

    step: int
    window_start: int
    window_end: int
    source: str
    target: str
    lag: int
    weight: float
    score: float
    sample_count: int


def compute_rolling_relation_weights(
    rows: Sequence[NumericRow],
    variables: Iterable[str],
    max_lag: int,
    steps: Iterable[int],
    window_size: int,
) -> List[TimedRelationWeight]:
    """Recompute static weights on a fixed-width causal window at each step.

    For step ``t``, the window ends at ``t`` exclusively. The estimate can use
    rows through ``t - 1`` but can never inspect row ``t`` or a future row.
    """
    if window_size <= max_lag:
        raise ValueError("window_size must be greater than max_lag")

    variable_names = tuple(variables)
    timed_weights: List[TimedRelationWeight] = []
    for step in steps:
        if step < 0 or step > len(rows):
            raise ValueError("steps must be within rows boundaries")
        window_start = max(0, step - window_size)
        history = rows[window_start:step]
        if len(history) <= max_lag:
            raise ValueError("each causal window must contain more rows than max_lag")

        weights = compute_lagged_relation_weights(
            history, variable_names, max_lag
        )
        for weight in weights:
            timed_weights.append(
                TimedRelationWeight(
                    step=step,
                    window_start=window_start,
                    window_end=step,
                    source=weight.source,
                    target=weight.target,
                    lag=weight.lag,
                    weight=weight.weight,
                    score=weight.score,
                    sample_count=weight.sample_count,
                )
            )
    return timed_weights


def rank_timed_target_sources(
    weights: Sequence[TimedRelationWeight], target: str, step: int
) -> Tuple[TimedRelationWeight, ...]:
    """Rank one target's source weights at one trajectory step."""
    selected = [
        weight
        for weight in weights
        if weight.target == target and weight.step == step
    ]
    if not selected:
        raise ValueError(f"no weights found for target {target!r} at step {step}")
    return tuple(sorted(selected, key=lambda item: (-item.score, item.source)))


def target_source_trajectory(
    weights: Sequence[TimedRelationWeight], target: str, source: str
) -> Tuple[TimedRelationWeight, ...]:
    """Extract one directed relation trajectory in chronological order."""
    selected = [
        weight
        for weight in weights
        if weight.target == target and weight.source == source
    ]
    return tuple(sorted(selected, key=lambda item: item.step))
