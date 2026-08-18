"""S10 fixtures for Evidence Gate and Prediction Confidence."""

from __future__ import annotations

import random
from dataclasses import dataclass
from statistics import mean
from typing import List, Sequence, Tuple

from .evidence_gate import (
    fixed_threshold_selection,
    precision_recall,
    select_relations_with_evidence,
)
from .prediction_confidence import (
    calibration_bins,
    compute_prediction_confidence,
    spearman_rank_correlation,
)
from .relation_weights import RelationWeight

FIXTURE_D_SEEDS = tuple(range(100))
TRUE_SOURCES = ("true_a", "true_b", "true_c")


@dataclass(frozen=True)
class FixtureDRun:
    seed: int
    fixed_precision: float
    fixed_recall: float
    gate_precision: float
    gate_recall: float
    fixed_selected_count: int
    gate_selected_count: int


@dataclass(frozen=True)
class FixtureDSummary:
    seed_count: int
    fixed_precision_mean: float
    fixed_recall_mean: float
    gate_precision_mean: float
    gate_recall_mean: float
    precision_lift: float
    recall_lift: float


@dataclass(frozen=True)
class ConfidenceCalibrationSummary:
    rank_correlation: float
    bins: Tuple[Tuple[float, float, int], ...]


def fixture_d_relations(seed: int) -> Tuple[RelationWeight, ...]:
    """Known mixed relation set: true, pseudo, and dead relations."""
    rng = random.Random(30_000 + seed)
    rows: List[RelationWeight] = []
    for index, source in enumerate(TRUE_SOURCES):
        sample_count = rng.randint(96, 144)
        score = 0.50 + rng.uniform(-0.08, 0.10)
        rows.append(
            RelationWeight(
                source=source,
                target="target",
                lag=index + 1,
                weight=score,
                score=score,
                sample_count=sample_count,
                transform="diff",
                stability=0.50 + rng.uniform(-0.04, 0.12),
                uncertainty=0.04 + rng.uniform(0.0, 0.09),
            )
        )
    pseudo_count = rng.randint(4, 7)
    for index in range(pseudo_count):
        sample_count = rng.randint(90, 150)
        score = 0.10 + rng.uniform(0.0, 0.26)
        rows.append(
            RelationWeight(
                source=f"pseudo_{index}",
                target="target",
                lag=1 + index % 3,
                weight=score if index % 2 == 0 else -score,
                score=score,
                sample_count=sample_count,
                transform="diff",
                stability=0.04 + rng.uniform(0.0, 0.28),
                uncertainty=0.13 + rng.uniform(0.0, 0.14),
            )
        )
    dead_count = rng.randint(2, 4)
    for index in range(dead_count):
        sample_count = rng.randint(96, 144)
        score = 0.44 + rng.uniform(-0.08, 0.13)
        rows.append(
            RelationWeight(
                source=f"dead_{index}",
                target="target",
                lag=1 + index % 3,
                weight=-score,
                score=score,
                sample_count=sample_count,
                transform="diff",
                stability=0.06 + rng.uniform(0.0, 0.22),
                uncertainty=0.20 + rng.uniform(0.0, 0.13),
            )
        )
    return tuple(rows)


def fixture_d_runs(seeds: Sequence[int] = FIXTURE_D_SEEDS) -> Tuple[FixtureDRun, ...]:
    runs: List[FixtureDRun] = []
    for seed in seeds:
        relations = fixture_d_relations(seed)
        fixed = fixed_threshold_selection(relations)
        gated = select_relations_with_evidence(relations, max_lag=3)
        fixed_precision, fixed_recall = precision_recall(
            [relation.source for relation in fixed], TRUE_SOURCES
        )
        gate_precision, gate_recall = precision_recall(
            [relation.source for relation in gated.selected_relations], TRUE_SOURCES
        )
        runs.append(
            FixtureDRun(
                seed=seed,
                fixed_precision=fixed_precision,
                fixed_recall=fixed_recall,
                gate_precision=gate_precision,
                gate_recall=gate_recall,
                fixed_selected_count=len(fixed),
                gate_selected_count=len(gated.selected_relations),
            )
        )
    return tuple(runs)


def fixture_d_summary(seeds: Sequence[int] = FIXTURE_D_SEEDS) -> FixtureDSummary:
    runs = fixture_d_runs(seeds)
    fixed_precision = mean(run.fixed_precision for run in runs)
    fixed_recall = mean(run.fixed_recall for run in runs)
    gate_precision = mean(run.gate_precision for run in runs)
    gate_recall = mean(run.gate_recall for run in runs)
    return FixtureDSummary(
        seed_count=len(runs),
        fixed_precision_mean=fixed_precision,
        fixed_recall_mean=fixed_recall,
        gate_precision_mean=gate_precision,
        gate_recall_mean=gate_recall,
        precision_lift=gate_precision - fixed_precision,
        recall_lift=gate_recall - fixed_recall,
    )


def confidence_calibration_fixture(
    seed: int = 0, count: int = 120
) -> ConfidenceCalibrationSummary:
    rng = random.Random(40_000 + seed)
    confidences: List[float] = []
    errors: List[float] = []
    for index in range(count):
        input_support = 1.0 - index / (count - 1)
        confidence = compute_prediction_confidence(
            relation_stability=0.70,
            parameter_uncertainty=0.08 + (1.0 - input_support) * 0.60,
            input_support=input_support,
            residual_uncertainty=0.10 + (1.0 - input_support) * 0.80,
        ).confidence
        if confidence is None:
            raise AssertionError("fixture should produce confidence")
        error_scale = 0.10 + (1.0 - confidence) * 1.40
        errors.append(abs(rng.gauss(0.0, error_scale)))
        confidences.append(confidence)
    return ConfidenceCalibrationSummary(
        rank_correlation=spearman_rank_correlation(confidences, errors),
        bins=calibration_bins(confidences, errors, bin_count=4),
    )
