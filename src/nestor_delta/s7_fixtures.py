"""S7 synthetic fixtures for transformed relationship measurement."""

from __future__ import annotations

import random
from dataclasses import dataclass
from statistics import median
from typing import Dict, Iterable, List, Sequence, Tuple

from .relation_weights import RelationWeight, legacy_level_scoring, rank_target_sources
from .stationarity import compute_transformed_relation_weights
from .synthetic import Row


@dataclass(frozen=True)
class FixtureSummary:
    fixture: str
    path: str
    seed_count: int
    median_abs_r: float
    p90_abs_r: float
    pass_rate_gt_006: float
    pass_rate_gt_030: float
    correct_lag_rate: float | None = None


FIXTURE_A_SEEDS = tuple(range(500))
FIXTURE_B_SEEDS = tuple(range(200))


def independent_random_walk_rows(seed: int, n: int = 216) -> Tuple[Row, ...]:
    rng = random.Random(seed)
    x = 0.0
    y = 0.0
    rows: List[Row] = []
    for index in range(n):
        x += rng.gauss(0.0, 1.0)
        y += rng.gauss(0.0, 1.0)
        rows.append({"x": x, "y": y, "time": float(index)})
    return tuple(rows)


def trended_lagged_difference_rows(seed: int, n: int = 216) -> Tuple[Row, ...]:
    rng = random.Random(10_000 + seed)
    x_level = 50.0
    y_level = 100.0
    dx_history: List[float] = []
    rows: List[Row] = []
    for index in range(n):
        dx = rng.gauss(0.0, 1.0)
        if index >= 3:
            dy = 0.6 * dx_history[index - 3] + rng.gauss(0.0, 0.8)
        else:
            dy = rng.gauss(0.0, 0.8)
        x_level += 0.30 + dx
        y_level += 0.20 + dy
        dx_history.append(dx)
        rows.append({"x": x_level, "y": y_level, "time": float(index)})
    return tuple(rows)


def fixture_a_summaries(max_lag: int = 5) -> Tuple[FixtureSummary, FixtureSummary]:
    legacy_scores: List[float] = []
    transformed_scores: List[float] = []
    for seed in FIXTURE_A_SEEDS:
        rows = independent_random_walk_rows(seed)
        legacy = _target_weight(
            legacy_level_scoring(rows, ("x", "y"), max_lag), "x", "y"
        )
        transformed = _target_weight(
            compute_transformed_relation_weights(
                rows, ("x", "y"), max_lag, {"x": "diff", "y": "diff"}
            ),
            "x",
            "y",
        )
        legacy_scores.append(legacy.score)
        transformed_scores.append(transformed.score)
    return (
        _summary("fixture_a_random_walk", "legacy_level_scoring", legacy_scores),
        _summary("fixture_a_random_walk", "s7_transformed_diff", transformed_scores),
    )


def fixture_b_summaries(max_lag: int = 5) -> Tuple[FixtureSummary, FixtureSummary]:
    legacy_scores: List[float] = []
    transformed_scores: List[float] = []
    transformed_lags: List[int] = []
    for seed in FIXTURE_B_SEEDS:
        rows = trended_lagged_difference_rows(seed)
        legacy = _target_weight(
            legacy_level_scoring(rows, ("x", "y"), max_lag), "x", "y"
        )
        transformed = _target_weight(
            compute_transformed_relation_weights(
                rows, ("x", "y"), max_lag, {"x": "diff", "y": "diff"}
            ),
            "x",
            "y",
        )
        legacy_scores.append(legacy.score)
        transformed_scores.append(transformed.score)
        transformed_lags.append(transformed.lag)
    correct_lag_rate = sum(1 for lag in transformed_lags if lag == 3) / len(
        transformed_lags
    )
    return (
        _summary("fixture_b_trended_dynamic", "legacy_level_scoring", legacy_scores),
        _summary(
            "fixture_b_trended_dynamic",
            "s7_transformed_diff",
            transformed_scores,
            correct_lag_rate,
        ),
    )


def _target_weight(
    weights: Sequence[RelationWeight], source: str, target: str
) -> RelationWeight:
    ranked = rank_target_sources(weights, target)
    for weight in ranked:
        if weight.source == source:
            return weight
    raise ValueError(f"missing {source}->{target} relation")


def _summary(
    fixture: str,
    path: str,
    scores: Sequence[float],
    correct_lag_rate: float | None = None,
) -> FixtureSummary:
    sorted_scores = sorted(scores)
    p90_index = int(0.9 * (len(sorted_scores) - 1))
    return FixtureSummary(
        fixture=fixture,
        path=path,
        seed_count=len(scores),
        median_abs_r=median(scores),
        p90_abs_r=sorted_scores[p90_index],
        pass_rate_gt_006=sum(1 for score in scores if score > 0.06) / len(scores),
        pass_rate_gt_030=sum(1 for score in scores if score > 0.30) / len(scores),
        correct_lag_rate=correct_lag_rate,
    )
