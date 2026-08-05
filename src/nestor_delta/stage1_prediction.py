"""Sprint 3 weighted three-variable prediction workflow."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Sequence, Tuple

from .baselines import fit_linear_regression, predict_linear_regression
from .config import FEATURE_COLUMNS, LAG_WINDOW
from .relation_weights import (
    RelationWeight,
    compute_lagged_relation_weights,
    rank_target_sources,
)
from .synthetic import Row


@dataclass(frozen=True)
class Stage1Model:
    """Fitted Stage 1 weighted predictor."""

    selected_weights: Tuple[RelationWeight, RelationWeight]
    coefficients: Tuple[float, ...]
    feature_names: Tuple[str, ...]


def fit_stage1_weighted_predictor(
    rows: Sequence[Row],
    train_label_rows: Iterable[int],
    target: str = "target",
    source_count: int = 2,
    lag_window: int = LAG_WINDOW,
) -> Stage1Model:
    """Fit the Sprint 3 weighted three-variable predictor.

    Relation weights are computed only on train rows, and only the top two
    non-target sources are used with the target's own lagged history.
    """
    train_label_rows = tuple(train_label_rows)
    if not train_label_rows:
        raise ValueError("train_label_rows must not be empty")

    train_end = max(train_label_rows) + 1
    train_history = rows[:train_end]
    all_weights = compute_lagged_relation_weights(train_history, FEATURE_COLUMNS, lag_window)
    selected = tuple(rank_target_sources(all_weights, target)[:source_count])
    if len(selected) != source_count:
        raise ValueError("not enough sources selected for Stage 1 predictor")

    train_features, train_labels = build_stage1_features(rows, train_label_rows, selected, target, lag_window)
    coefficients = fit_linear_regression(train_features, train_labels)
    feature_names = tuple(stage1_feature_names(selected, target, lag_window))
    return Stage1Model(
        selected_weights=selected,
        coefficients=tuple(coefficients),
        feature_names=feature_names,
    )


def predict_stage1_weighted(
    rows: Sequence[Row],
    label_rows: Iterable[int],
    model: Stage1Model,
    target: str = "target",
    lag_window: int = LAG_WINDOW,
) -> List[float]:
    features, _ = build_stage1_features(rows, label_rows, model.selected_weights, target, lag_window)
    return predict_linear_regression(features, model.coefficients)


def build_stage1_features(
    rows: Sequence[Row],
    label_rows: Iterable[int],
    selected_weights: Sequence[RelationWeight],
    target: str = "target",
    lag_window: int = LAG_WINDOW,
) -> Tuple[List[List[float]], List[float]]:
    """Build target + top-source lag features for label rows.

    For label row i, all features use rows <= i - 1. Source features are scaled
    by their Sprint 2 signed relation weight.
    """
    features: List[List[float]] = []
    labels: List[float] = []
    for label_index in label_rows:
        sample = [1.0]
        for lag in range(1, lag_window + 1):
            sample.append(float(rows[label_index - lag][target]))
            for weight in selected_weights:
                sample.append(float(rows[label_index - lag][weight.source]) * weight.weight)
        features.append(sample)
        labels.append(float(rows[label_index][target]))
    return features, labels


def stage1_feature_names(
    selected_weights: Sequence[RelationWeight],
    target: str = "target",
    lag_window: int = LAG_WINDOW,
) -> List[str]:
    names = ["intercept"]
    for lag in range(1, lag_window + 1):
        names.append(f"{target}_lag{lag}")
        for weight in selected_weights:
            names.append(f"{weight.source}_lag{lag}_weighted")
    return names
