"""Sprint 4 prediction comparison using static or causal rolling weights."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Mapping, Sequence, Tuple

from .baselines import fit_linear_regression, predict_linear_regression
from .config import FEATURE_COLUMNS, LAG_WINDOW
from .dynamic_weights import TimedRelationWeight, compute_rolling_relation_weights
from .relation_weights import (
    RelationWeight,
    compute_lagged_relation_weights,
    rank_target_sources,
)
from .s4_config import DYNAMIC_WINDOW
from .synthetic import Row


@dataclass(frozen=True)
class StaticDriftModel:
    """Train-only predictor whose relation weights remain fixed."""

    selected_weights: Tuple[RelationWeight, ...]
    coefficients: Tuple[float, ...]
    feature_names: Tuple[str, ...]


@dataclass(frozen=True)
class DynamicDriftModel:
    """Predictor fitted with causal rolling relation-weight features."""

    selected_sources: Tuple[str, ...]
    coefficients: Tuple[float, ...]
    feature_names: Tuple[str, ...]
    window_size: int


def fit_static_drift_predictor(
    rows: Sequence[Row],
    train_label_rows: Iterable[int],
    target: str = "target",
    source_count: int = 2,
    lag_window: int = LAG_WINDOW,
) -> StaticDriftModel:
    """Fit the fixed-weight comparator on train-only history."""
    train_label_rows = tuple(train_label_rows)
    if not train_label_rows:
        raise ValueError("train_label_rows must not be empty")

    train_end = max(train_label_rows) + 1
    weights = compute_lagged_relation_weights(
        rows[:train_end], FEATURE_COLUMNS, lag_window
    )
    selected = tuple(rank_target_sources(weights, target)[:source_count])
    if len(selected) != source_count:
        raise ValueError("not enough sources selected for static predictor")

    weights_by_step = {
        label_index: _relation_weight_map(selected, target)
        for label_index in train_label_rows
    }
    features, labels = build_weighted_relation_features(
        rows, train_label_rows, weights_by_step, target, lag_window
    )
    coefficients = fit_linear_regression(features, labels)
    return StaticDriftModel(
        selected_weights=selected,
        coefficients=tuple(coefficients),
        feature_names=tuple(dynamic_feature_names(target, lag_window)),
    )


def predict_static_drift(
    rows: Sequence[Row],
    label_rows: Iterable[int],
    model: StaticDriftModel,
    target: str = "target",
    lag_window: int = LAG_WINDOW,
) -> List[float]:
    """Predict with relation weights frozen at their train-only values."""
    label_rows = tuple(label_rows)
    static_map = _relation_weight_map(model.selected_weights, target)
    weights_by_step = {label_index: static_map for label_index in label_rows}
    features, _ = build_weighted_relation_features(
        rows, label_rows, weights_by_step, target, lag_window
    )
    return predict_linear_regression(features, model.coefficients)


def fit_dynamic_drift_predictor(
    rows: Sequence[Row],
    train_label_rows: Iterable[int],
    target: str = "target",
    source_count: int = 2,
    lag_window: int = LAG_WINDOW,
    window_size: int = DYNAMIC_WINDOW,
) -> DynamicDriftModel:
    """Fit OLS on train-only samples transformed by causal rolling weights."""
    train_label_rows = tuple(train_label_rows)
    if not train_label_rows:
        raise ValueError("train_label_rows must not be empty")
    if min(train_label_rows) < window_size:
        raise ValueError("train_label_rows must begin after the rolling warm-up")

    train_end = max(train_label_rows) + 1
    selection_weights = compute_lagged_relation_weights(
        rows[:train_end], FEATURE_COLUMNS, lag_window
    )
    selected_sources = tuple(
        weight.source
        for weight in rank_target_sources(selection_weights, target)[:source_count]
    )
    if len(selected_sources) != source_count:
        raise ValueError("not enough sources selected for dynamic predictor")

    timed_weights = compute_rolling_relation_weights(
        rows,
        FEATURE_COLUMNS,
        lag_window,
        train_label_rows,
        window_size,
    )
    weights_by_step = _timed_weight_maps(
        timed_weights, train_label_rows, selected_sources, target
    )
    features, labels = build_weighted_relation_features(
        rows, train_label_rows, weights_by_step, target, lag_window
    )
    coefficients = fit_linear_regression(features, labels)
    return DynamicDriftModel(
        selected_sources=selected_sources,
        coefficients=tuple(coefficients),
        feature_names=tuple(dynamic_feature_names(target, lag_window)),
        window_size=window_size,
    )


def predict_dynamic_drift(
    rows: Sequence[Row],
    label_rows: Iterable[int],
    model: DynamicDriftModel,
    target: str = "target",
    lag_window: int = LAG_WINDOW,
) -> Tuple[List[float], Tuple[TimedRelationWeight, ...]]:
    """Predict prequentially, updating weights only from rows before each label."""
    label_rows = tuple(label_rows)
    timed_weights = tuple(
        compute_rolling_relation_weights(
            rows,
            FEATURE_COLUMNS,
            lag_window,
            label_rows,
            model.window_size,
        )
    )
    weights_by_step = _timed_weight_maps(
        timed_weights, label_rows, model.selected_sources, target
    )
    features, _ = build_weighted_relation_features(
        rows, label_rows, weights_by_step, target, lag_window
    )
    predictions = predict_linear_regression(features, model.coefficients)
    return predictions, timed_weights


def build_weighted_relation_features(
    rows: Sequence[Row],
    label_rows: Iterable[int],
    weights_by_step: Mapping[int, Mapping[str, float]],
    target: str = "target",
    lag_window: int = LAG_WINDOW,
) -> Tuple[List[List[float]], List[float]]:
    """Build target history plus one shared weighted source signal per lag."""
    features: List[List[float]] = []
    labels: List[float] = []
    for label_index in label_rows:
        source_weights = weights_by_step[label_index]
        sample = [1.0]
        for lag in range(1, lag_window + 1):
            history_row = rows[label_index - lag]
            sample.append(float(history_row[target]))
            sample.append(
                sum(
                    weight * float(history_row[source])
                    for source, weight in source_weights.items()
                )
            )
        features.append(sample)
        labels.append(float(rows[label_index][target]))
    return features, labels


def dynamic_feature_names(
    target: str = "target", lag_window: int = LAG_WINDOW
) -> List[str]:
    names = ["intercept"]
    for lag in range(1, lag_window + 1):
        names.append(f"{target}_lag{lag}")
        names.append(f"weighted_relation_signal_lag{lag}")
    return names


def _relation_weight_map(
    weights: Sequence[RelationWeight], target: str
) -> Dict[str, float]:
    return {
        weight.source: weight.weight
        for weight in weights
        if weight.target == target
    }


def _timed_weight_maps(
    weights: Sequence[TimedRelationWeight],
    steps: Sequence[int],
    sources: Sequence[str],
    target: str,
) -> Dict[int, Dict[str, float]]:
    selected = {
        (weight.step, weight.source): weight.weight
        for weight in weights
        if weight.target == target and weight.source in sources
    }
    result: Dict[int, Dict[str, float]] = {}
    for step in steps:
        result[step] = {source: selected[(step, source)] for source in sources}
    return result
