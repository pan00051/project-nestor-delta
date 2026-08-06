"""Sprint 5 prediction with resource-adaptive relation ignoring."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Sequence, Tuple

from .baselines import fit_linear_regression, predict_linear_regression
from .relation_weights import RelationWeight, compute_lagged_relation_weights
from .resource_adaptive_ignore import (
    DEFAULT_IGNORE_CONFIG,
    DownstreamResourceProfile,
    ResourceAdaptiveIgnoreConfig,
    downstream_profile,
    retain_relations,
    threshold_for_budget,
)
from .synthetic import Row


@dataclass(frozen=True)
class AdaptiveIgnoreModel:
    """OLS model using target history and retained relation signals."""

    budget_ratio: float
    threshold: float
    retained_relations: Tuple[RelationWeight, ...]
    coefficients: Tuple[float, ...]
    feature_names: Tuple[str, ...]
    profile: DownstreamResourceProfile


def fit_adaptive_ignore_predictor(
    rows: Sequence[Row],
    train_label_rows: Iterable[int],
    variables: Sequence[str],
    budget_ratio: float,
    target: str = "target",
    lag_window: int = 5,
    config: ResourceAdaptiveIgnoreConfig = DEFAULT_IGNORE_CONFIG,
) -> AdaptiveIgnoreModel:
    """Fit a deterministic downstream predictor after adaptive ignoring."""
    train_label_rows = tuple(train_label_rows)
    if not train_label_rows:
        raise ValueError("train_label_rows must not be empty")

    train_end = max(train_label_rows) + 1
    weights = compute_lagged_relation_weights(rows[:train_end], variables, lag_window)
    retained = retain_relations(weights, target, budget_ratio, config)
    features, labels = build_adaptive_ignore_features(
        rows, train_label_rows, retained, target, lag_window
    )
    coefficients = fit_linear_regression(features, labels)
    profile = downstream_profile(
        budget_ratio=budget_ratio,
        retained_relation_count=len(retained),
        downstream_lag_count=lag_window,
        materialized_lag_count=lag_window,
        effective_row_count=len(train_label_rows),
        config=config,
    )
    return AdaptiveIgnoreModel(
        budget_ratio=budget_ratio,
        threshold=threshold_for_budget(budget_ratio, config),
        retained_relations=retained,
        coefficients=tuple(coefficients),
        feature_names=tuple(
            adaptive_ignore_feature_names(target, lag_window, bool(retained))
        ),
        profile=profile,
    )


def predict_adaptive_ignore(
    rows: Sequence[Row],
    label_rows: Iterable[int],
    model: AdaptiveIgnoreModel,
    target: str = "target",
    lag_window: int = 5,
) -> List[float]:
    features, _ = build_adaptive_ignore_features(
        rows, label_rows, model.retained_relations, target, lag_window
    )
    return predict_linear_regression(features, model.coefficients)


def build_adaptive_ignore_features(
    rows: Sequence[Row],
    label_rows: Iterable[int],
    retained_relations: Sequence[RelationWeight],
    target: str = "target",
    lag_window: int = 5,
) -> Tuple[List[List[float]], List[float]]:
    """Build target history plus one retained weighted relation mixture per lag."""
    features: List[List[float]] = []
    labels: List[float] = []
    for label_index in label_rows:
        sample = [1.0]
        for lag in range(1, lag_window + 1):
            history_row = rows[label_index - lag]
            sample.append(float(history_row[target]))
            if retained_relations:
                sample.append(
                    sum(
                        relation.weight * float(history_row[relation.source])
                        for relation in retained_relations
                    )
            )
        features.append(sample)
        labels.append(float(rows[label_index][target]))
    return features, labels


def adaptive_ignore_feature_names(
    target: str = "target", lag_window: int = 5, has_relations: bool = True
) -> List[str]:
    names = ["intercept"]
    for lag in range(1, lag_window + 1):
        names.append(f"{target}_lag{lag}")
        if has_relations:
            names.append(f"retained_relation_signal_lag{lag}")
    return names
