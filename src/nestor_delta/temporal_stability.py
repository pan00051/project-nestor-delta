"""S9 temporal stability and relation lifecycle statistics."""

from __future__ import annotations

from dataclasses import dataclass
from statistics import mean, pstdev
from typing import Literal, Sequence

from .dynamic_weights import TimedRelationWeight
from .relation_weights import RelationWeight

LifecycleState = Literal["birth", "strengthening", "stable", "decaying", "dead"]


@dataclass(frozen=True)
class RelationLifecycle:
    """S9 relation object plus its lifecycle state."""

    relation: RelationWeight
    state: LifecycleState
    points: int


def aggregate_relation_trajectory(
    trajectory: Sequence[TimedRelationWeight],
    *,
    min_points: int = 6,
    recent_points: int = 5,
    selected: bool | None = None,
) -> RelationWeight:
    """Compress one target-source trajectory into S9 stability statistics.

    S9 is deliberately descriptive: ``selected`` is copied from the caller if it
    already exists, but this function does not perform an Evidence Gate.
    """
    if not trajectory:
        raise ValueError("trajectory must contain at least one point")
    if min_points < 2:
        raise ValueError("min_points must be at least 2")
    if recent_points < 2:
        raise ValueError("recent_points must be at least 2")

    ordered = tuple(sorted(trajectory, key=lambda item: item.step))
    latest = ordered[-1]
    if len(ordered) < min_points:
        return _relation_from_latest(
            latest, stability=None, uncertainty=None, selected=selected
        )

    recent = ordered[-recent_points:]
    recent_scores = [item.score for item in recent]
    latest_sign = _sign(latest.weight)
    sign_consistency = sum(
        1 for item in recent if _sign(item.weight) == latest_sign and latest_sign != 0
    ) / len(recent)
    lag_consistency = sum(1 for item in recent if item.lag == latest.lag) / len(recent)
    strength = mean(recent_scores)
    stability = max(0.0, min(1.0, strength * sign_consistency * lag_consistency))
    uncertainty = pstdev([item.weight for item in recent])

    return _relation_from_latest(
        latest,
        stability=stability,
        uncertainty=uncertainty,
        selected=selected,
    )


def classify_relation_lifecycle(
    trajectory: Sequence[TimedRelationWeight],
    *,
    min_points: int = 6,
    recent_points: int = 5,
    score_floor: float = 0.20,
    stable_floor: float = 0.45,
    dead_points: int = 5,
) -> RelationLifecycle:
    """Assign the S9 lifecycle state for one directed relation trajectory."""
    relation = aggregate_relation_trajectory(
        trajectory, min_points=min_points, recent_points=recent_points
    )
    ordered = tuple(sorted(trajectory, key=lambda item: item.step))
    if len(ordered) < min_points:
        return RelationLifecycle(relation=relation, state="birth", points=len(ordered))

    scores = [item.score for item in ordered]
    recent_scores = scores[-recent_points:]
    prior_scores = scores[:-recent_points]
    recent_mean = mean(recent_scores)
    prior_mean = mean(prior_scores) if prior_scores else recent_mean
    slope = _least_squares_slope(scores[-max(recent_points * 2, 3) :])

    # S9 endorsement threshold: a relation must clear stability AND strength
    # before it can be labeled stable or strengthening. Pure noise on the
    # transformed path tops out near 0.36 stability, below stable_floor, so it
    # stays birth/decaying/dead.
    meets_endorsement_threshold = (
        relation.stability is not None
        and relation.stability >= stable_floor
        and recent_mean >= score_floor
    )
    rising = recent_mean > prior_mean + 0.08 and slope > 0.01
    if len(scores) >= dead_points and all(score < score_floor for score in scores[-dead_points:]):
        state: LifecycleState = "dead"
    elif prior_mean >= score_floor and (
        recent_mean < prior_mean * 0.65
        or (slope < -0.025 and recent_mean < prior_mean - 0.08)
    ):
        state = "decaying"
    elif meets_endorsement_threshold and rising:
        state = "strengthening"
    elif meets_endorsement_threshold:
        state = "stable"
    else:
        state = "birth"

    return RelationLifecycle(relation=relation, state=state, points=len(ordered))


def _relation_from_latest(
    latest: TimedRelationWeight,
    *,
    stability: float | None,
    uncertainty: float | None,
    selected: bool | None,
) -> RelationWeight:
    return RelationWeight(
        source=latest.source,
        target=latest.target,
        lag=latest.lag,
        weight=latest.weight,
        score=latest.score,
        sample_count=latest.sample_count,
        transform=latest.transform,
        stability=stability,
        uncertainty=uncertainty,
        selected=selected,
    )


def _sign(value: float) -> int:
    if value > 0.0:
        return 1
    if value < 0.0:
        return -1
    return 0


def _least_squares_slope(values: Sequence[float]) -> float:
    if len(values) < 2:
        return 0.0
    x_mean = (len(values) - 1) / 2.0
    y_mean = mean(values)
    numerator = 0.0
    denominator = 0.0
    for index, value in enumerate(values):
        x_delta = index - x_mean
        numerator += x_delta * (value - y_mean)
        denominator += x_delta * x_delta
    if denominator == 0.0:
        return 0.0
    return numerator / denominator
