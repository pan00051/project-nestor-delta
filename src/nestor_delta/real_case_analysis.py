"""Sprint 6 real-data case analysis built on frozen Delta capabilities."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Sequence, Tuple

from .baselines import fit_linear_regression, predict_linear_regression
from .metrics import mae, rmse
from .real_data import RealCaseConfig, RealCaseData, real_case_label_rows
from .relation_weights import (
    RelationWeight,
    compute_lagged_relation_weights,
    rank_target_sources,
)
from .resource_adaptive_ignore import (
    DEFAULT_IGNORE_CONFIG,
    downstream_profile,
    retain_relations,
)
from .s5_config import BUDGET_RATIOS
from .synthetic import Row


@dataclass(frozen=True)
class RealCaseModel:
    selected_weights: Tuple[RelationWeight, ...]
    coefficients: Tuple[float, ...]
    feature_names: Tuple[str, ...]
    fit_status: str
    dropped_collinear_sources: Tuple[str, ...]


@dataclass(frozen=True)
class RealCaseResult:
    ranking: Tuple[RelationWeight, ...]
    selected_weights: Tuple[RelationWeight, ...]
    metric_rows: Tuple[Dict[str, object], ...]
    prediction_rows: Tuple[Dict[str, object], ...]
    resource_rows: Tuple[Dict[str, object], ...]
    train_label_rows: Tuple[int, ...]
    test_label_rows: Tuple[int, ...]
    fit_status: str
    dropped_collinear_sources: Tuple[str, ...]
    model_coefficients: Tuple[float, ...]


def run_real_case_analysis(
    config: RealCaseConfig, data: RealCaseData
) -> RealCaseResult:
    """Run train-only ranking, prediction, and resource summaries."""
    train_label_rows, test_label_rows = real_case_label_rows(data.dates, config)
    train_end = max(train_label_rows) + 1
    relation_weights = compute_lagged_relation_weights(
        data.rows[:train_end],
        data.variables,
        config.lag_window,
    )
    ranking = _stable_target_ranking(relation_weights, config.target)
    model = fit_real_case_predictor_with_backoff(
        data.rows,
        train_label_rows,
        ranking[: config.max_selected_signals],
        config.target,
        config.lag_window,
    )
    selected = model.selected_weights

    labels = [float(data.rows[index][config.target]) for index in test_label_rows]
    persistence = predict_persistence(data.rows, test_label_rows, config.target)
    seasonal = (
        predict_seasonal_naive(
            data.rows, test_label_rows, config.target, config.seasonal_period
        )
        if config.seasonal_period > 0
        else None
    )

    metric_rows = [_metric_row("persistence", labels, persistence)]
    predictions = None
    if model.fit_status != "baseline_only_no_stable_signal":
        predictions = predict_real_case(
            data.rows, test_label_rows, model, config.target, config.lag_window
        )
        metric_rows.append(_metric_row("delta_selected_signals", labels, predictions))
    if seasonal is not None:
        metric_rows.append(_metric_row("seasonal_naive", labels, seasonal))

    prediction_rows = []
    for offset, index in enumerate(test_label_rows):
        row = {
            "date": data.dates[index],
            "actual": labels[offset],
            "persistence": persistence[offset],
        }
        if predictions is not None:
            row["delta_selected_signals"] = predictions[offset]
        if seasonal is not None:
            row["seasonal_naive"] = seasonal[offset]
        prediction_rows.append(row)

    resource_rows = []
    for budget_ratio in BUDGET_RATIOS:
        retained = retain_relations(
            relation_weights,
            config.target,
            budget_ratio,
            DEFAULT_IGNORE_CONFIG,
        )
        profile = downstream_profile(
            budget_ratio=budget_ratio,
            retained_relation_count=len(retained),
            downstream_lag_count=config.lag_window,
            materialized_lag_count=config.lag_window,
            effective_row_count=len(train_label_rows),
        )
        resource_rows.append(
            {
                "budget_ratio": budget_ratio,
                "threshold": profile.threshold,
                "retained_relation_count": profile.retained_relation_count,
                "downstream_compute_proxy": profile.downstream_compute_proxy,
                "downstream_memory_proxy": profile.downstream_memory_proxy,
                "retained_sources": ";".join(relation.source for relation in retained),
            }
        )

    return RealCaseResult(
        ranking=ranking,
        selected_weights=tuple(selected),
        metric_rows=tuple(metric_rows),
        prediction_rows=tuple(prediction_rows),
        resource_rows=tuple(resource_rows),
        train_label_rows=train_label_rows,
        test_label_rows=test_label_rows,
        fit_status=model.fit_status,
        dropped_collinear_sources=model.dropped_collinear_sources,
        model_coefficients=model.coefficients,
    )


def fit_real_case_predictor(
    rows: Sequence[Row],
    train_label_rows: Iterable[int],
    selected_weights: Sequence[RelationWeight],
    target: str,
    lag_window: int,
) -> RealCaseModel:
    features, labels = build_real_case_features(
        rows, train_label_rows, selected_weights, target, lag_window
    )
    coefficients = fit_linear_regression(features, labels)
    return RealCaseModel(
        selected_weights=tuple(selected_weights),
        coefficients=tuple(coefficients),
        feature_names=tuple(_feature_names(selected_weights, target, lag_window)),
        fit_status="fit",
        dropped_collinear_sources=(),
    )


def fit_real_case_predictor_with_backoff(
    rows: Sequence[Row],
    train_label_rows: Iterable[int],
    selected_weights: Sequence[RelationWeight],
    target: str,
    lag_window: int,
) -> RealCaseModel:
    """Fit with fewer selected signals if real data is collinear."""
    selected_weights = tuple(selected_weights)
    active = selected_weights
    dropped: List[str] = []
    while active:
        try:
            model = fit_real_case_predictor(rows, train_label_rows, active, target, lag_window)
            return RealCaseModel(
                selected_weights=model.selected_weights,
                coefficients=model.coefficients,
                feature_names=model.feature_names,
                fit_status=("fit" if not dropped else "fit_after_collinearity_backoff"),
                dropped_collinear_sources=tuple(dropped),
            )
        except ValueError as exc:
            if "singular or ill-conditioned" not in str(exc):
                raise
            drop_index = _collinear_lower_rank_index(
                rows, tuple(train_label_rows), active, lag_window
            )
            dropped.append(active[drop_index].source)
            active = active[:drop_index] + active[drop_index + 1 :]
    return RealCaseModel(
        selected_weights=(),
        coefficients=(),
        feature_names=(),
        fit_status="baseline_only_no_stable_signal",
        dropped_collinear_sources=tuple(dropped),
    )


def predict_real_case(
    rows: Sequence[Row],
    label_rows: Iterable[int],
    model: RealCaseModel,
    target: str,
    lag_window: int,
) -> List[float]:
    features, _ = build_real_case_features(
        rows, label_rows, model.selected_weights, target, lag_window
    )
    return predict_linear_regression(features, model.coefficients)


def build_real_case_features(
    rows: Sequence[Row],
    label_rows: Iterable[int],
    selected_weights: Sequence[RelationWeight],
    target: str,
    lag_window: int,
) -> Tuple[List[List[float]], List[float]]:
    features: List[List[float]] = []
    labels: List[float] = []
    for label_index in label_rows:
        sample = [1.0]
        for lag in range(1, lag_window + 1):
            history_row = rows[label_index - lag]
            sample.append(float(history_row[target]))
            for weight in selected_weights:
                sample.append(float(history_row[weight.source]) * weight.weight)
        features.append(sample)
        labels.append(float(rows[label_index][target]))
    return features, labels


def predict_persistence(
    rows: Sequence[Row], label_rows: Iterable[int], target: str
) -> List[float]:
    return [float(rows[index - 1][target]) for index in label_rows]


def predict_seasonal_naive(
    rows: Sequence[Row], label_rows: Iterable[int], target: str, seasonal_period: int
) -> List[float]:
    predictions = []
    for index in label_rows:
        seasonal_index = index - seasonal_period
        if seasonal_index < 0:
            predictions.append(float(rows[index - 1][target]))
        else:
            predictions.append(float(rows[seasonal_index][target]))
    return predictions


def _metric_row(
    method: str, labels: Sequence[float], predictions: Sequence[float]
) -> Dict[str, object]:
    return {
        "method": method,
        "mae": mae(labels, predictions),
        "rmse": rmse(labels, predictions),
        "sample_count": len(labels),
    }


def _stable_target_ranking(
    relation_weights: Sequence[RelationWeight], target: str
) -> Tuple[RelationWeight, ...]:
    return tuple(
        sorted(
            rank_target_sources(relation_weights, target),
            key=lambda weight: (-weight.score, weight.source, weight.lag),
        )
    )


def _collinear_lower_rank_index(
    rows: Sequence[Row],
    train_label_rows: Tuple[int, ...],
    selected_weights: Sequence[RelationWeight],
    lag_window: int,
) -> int:
    vectors = [
        _source_history_vector(rows, train_label_rows, weight, lag_window)
        for weight in selected_weights
    ]
    for left_index in range(len(vectors)):
        for right_index in range(left_index + 1, len(vectors)):
            if _vectors_collinear(vectors[left_index], vectors[right_index]):
                return right_index
    return len(selected_weights) - 1


def _source_history_vector(
    rows: Sequence[Row],
    train_label_rows: Tuple[int, ...],
    weight: RelationWeight,
    lag_window: int,
) -> Tuple[float, ...]:
    values: List[float] = []
    for label_index in train_label_rows:
        for lag in range(1, lag_window + 1):
            values.append(float(rows[label_index - lag][weight.source]))
    return tuple(values)


def _vectors_collinear(left: Sequence[float], right: Sequence[float]) -> bool:
    scale: float | None = None
    for left_value, right_value in zip(left, right):
        if abs(left_value) < 1e-12 and abs(right_value) < 1e-12:
            continue
        if abs(left_value) < 1e-12 or abs(right_value) < 1e-12:
            return False
        current = right_value / left_value
        if scale is None:
            scale = current
        elif abs(current - scale) > 1e-10:
            return False
    return scale is not None


def _feature_names(
    selected_weights: Sequence[RelationWeight], target: str, lag_window: int
) -> List[str]:
    names = ["intercept"]
    for lag in range(1, lag_window + 1):
        names.append(f"{target}_lag{lag}")
        for weight in selected_weights:
            names.append(f"{weight.source}_lag{lag}_weighted")
    return names
