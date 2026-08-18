"""S9 fixtures for temporal stability and relation lifecycle."""

from __future__ import annotations

import random
from dataclasses import dataclass
from statistics import median
from typing import List, Sequence, Tuple

from .dynamic_weights import (
    TimedRelationWeight,
    compute_rolling_transformed_relation_weights,
    target_source_trajectory,
)
from .s7_fixtures import independent_random_walk_rows
from .synthetic import Row
from .temporal_stability import aggregate_relation_trajectory, classify_relation_lifecycle

FIXTURE_C_SEEDS = tuple(range(100))
FIXTURE_C_DEATH_STEP = 120
FIXTURE_C_K = 30
FIXTURE_C_MAX_LAG = 3
FIXTURE_C_WINDOW = 36


@dataclass(frozen=True)
class DetectionLagSummary:
    fixture: str
    seed_count: int
    detected_count: int
    k_step_success_rate: float
    median_detection_lag: float | None
    detection_lags: Tuple[int, ...]


def relation_death_rows(
    seed: int,
    *,
    n: int = 180,
    death_step: int = FIXTURE_C_DEATH_STEP,
    true_lag: int = 3,
) -> Tuple[Row, ...]:
    """Build a trended level fixture whose transformed relation dies at T."""
    rng = random.Random(20_000 + seed)
    x_level = 50.0
    y_level = 100.0
    dx_history: List[float] = []
    rows: List[Row] = []
    for index in range(n):
        dx = rng.gauss(0.0, 1.0)
        if index >= true_lag and index < death_step:
            dy = 0.9 * dx_history[index - true_lag] + rng.gauss(0.0, 0.45)
        else:
            dy = rng.gauss(0.0, 0.45)
        x_level += 0.25 + dx
        y_level += 0.15 + dy
        dx_history.append(dx)
        rows.append({"x": x_level, "y": y_level, "time": float(index)})
    return tuple(rows)


def fixture_c_detection_lags(
    *,
    seeds: Sequence[int] = FIXTURE_C_SEEDS,
    death_step: int = FIXTURE_C_DEATH_STEP,
    k_steps: int = FIXTURE_C_K,
) -> Tuple[int | None, ...]:
    lags: List[int | None] = []
    for seed in seeds:
        rows = relation_death_rows(seed, death_step=death_step)
        steps = range(FIXTURE_C_WINDOW + FIXTURE_C_MAX_LAG + 1, len(rows) + 1)
        weights = compute_rolling_transformed_relation_weights(
            rows,
            ("x", "y"),
            FIXTURE_C_MAX_LAG,
            steps,
            FIXTURE_C_WINDOW,
            {"x": "diff", "y": "diff"},
        )
        detected: int | None = None
        for step in steps:
            if step < death_step:
                continue
            prefix = [weight for weight in weights if weight.step <= step]
            trajectory = target_source_trajectory(prefix, "y", "x")
            state = classify_relation_lifecycle(trajectory).state
            if state == "decaying":
                detected = step - death_step
                break
        if detected is not None and detected <= k_steps:
            lags.append(detected)
        else:
            lags.append(None)
    return tuple(lags)


def fixture_c_summary(
    *,
    seeds: Sequence[int] = FIXTURE_C_SEEDS,
    death_step: int = FIXTURE_C_DEATH_STEP,
    k_steps: int = FIXTURE_C_K,
) -> DetectionLagSummary:
    lags = fixture_c_detection_lags(
        seeds=seeds, death_step=death_step, k_steps=k_steps
    )
    detected_lags = tuple(lag for lag in lags if lag is not None)
    return DetectionLagSummary(
        fixture="fixture_c_relation_death",
        seed_count=len(lags),
        detected_count=len(detected_lags),
        k_step_success_rate=len(detected_lags) / len(lags),
        median_detection_lag=(
            float(median(detected_lags)) if detected_lags else None
        ),
        detection_lags=detected_lags,
    )


def fixture_a_transformed_stability_scores(
    *,
    seeds: Sequence[int] = tuple(range(50)),
    max_lag: int = 3,
    window_size: int = 36,
) -> Tuple[float, ...]:
    """Measure S9 stability on S7 transformed independent random walks."""
    stability_scores: List[float] = []
    for seed in seeds:
        rows = independent_random_walk_rows(seed)
        steps = range(window_size + max_lag + 1, len(rows) + 1, 6)
        weights = compute_rolling_transformed_relation_weights(
            rows,
            ("x", "y"),
            max_lag,
            steps,
            window_size,
            {"x": "diff", "y": "diff"},
        )
        relation = aggregate_relation_trajectory(
            target_source_trajectory(weights, "y", "x")
        )
        if relation.stability is not None:
            stability_scores.append(relation.stability)
    return tuple(stability_scores)


def fixture_a_transformed_lifecycle_states(
    *,
    seeds: Sequence[int] = tuple(range(50)),
    max_lag: int = 3,
    window_size: int = 36,
) -> Tuple[str, ...]:
    """Classify S7 transformed independent random walks into lifecycle states.

    The guard that matters downstream is the STATE, not the stability score:
    no pure-noise trajectory may be endorsed as ``stable`` or ``strengthening``.
    """
    states: List[str] = []
    for seed in seeds:
        rows = independent_random_walk_rows(seed)
        steps = range(window_size + max_lag + 1, len(rows) + 1, 6)
        weights = compute_rolling_transformed_relation_weights(
            rows,
            ("x", "y"),
            max_lag,
            steps,
            window_size,
            {"x": "diff", "y": "diff"},
        )
        states.append(
            classify_relation_lifecycle(
                target_source_trajectory(weights, "y", "x")
            ).state
        )
    return tuple(states)
