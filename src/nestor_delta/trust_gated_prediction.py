"""Trust-gated prediction composed from frozen Sprint 1-3 modules."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Literal, Optional, Sequence, Tuple, Union

from .baselines import fit_linear_regression, predict_linear_regression
from .config import FEATURE_COLUMNS, LAG_WINDOW
from .relation_weights import RelationWeight, compute_lagged_relation_weights
from .stage1_prediction import (
    Stage1Model,
    fit_stage1_weighted_predictor,
    predict_stage1_weighted,
)
from .synthetic import Row
from .trust_gating import (
    DEFAULT_GATE_CONFIG,
    TrustGate,
    TrustGateConfig,
    build_trust_gates,
    combine_gated_signals,
)

PredictionMode = Literal["ols", "trust_gated"]


@dataclass(frozen=True)
class TrustGatedModel:
    """OLS predictor fitted on target history and gated composite signals."""

    gates: Tuple[TrustGate, ...]
    coefficients: Tuple[float, ...]
    feature_names: Tuple[str, ...]


PredictionModel = Union[Stage1Model, TrustGatedModel]


def fit_prediction_mode(
    rows: Sequence[Row],
    train_label_rows: Iterable[int],
    mode: PredictionMode,
    gate_config: TrustGateConfig = DEFAULT_GATE_CONFIG,
) -> PredictionModel:
    """Fit either the frozen Sprint 3 OLS mode or the new gated mode."""
    if mode == "ols":
        return fit_stage1_weighted_predictor(rows, train_label_rows)
    if mode == "trust_gated":
        return fit_trust_gated_predictor(rows, train_label_rows, gate_config=gate_config)
    raise ValueError(f"unknown prediction mode: {mode!r}")


def predict_with_mode(
    rows: Sequence[Row],
    label_rows: Iterable[int],
    model: PredictionModel,
    mode: PredictionMode,
) -> List[float]:
    """Predict with the model type selected by ``mode``."""
    if mode == "ols" and isinstance(model, Stage1Model):
        return predict_stage1_weighted(rows, label_rows, model)
    if mode == "trust_gated" and isinstance(model, TrustGatedModel):
        return predict_trust_gated(rows, label_rows, model)
    raise TypeError("model does not match prediction mode")


def fit_trust_gated_predictor(
    rows: Sequence[Row],
    train_label_rows: Iterable[int],
    target: str = "target",
    lag_window: int = LAG_WINDOW,
    gate_config: TrustGateConfig = DEFAULT_GATE_CONFIG,
    relation_weights: Optional[Sequence[RelationWeight]] = None,
) -> TrustGatedModel:
    """Fit OLS after relation signals pass through train-only trust gates."""
    train_label_rows = tuple(train_label_rows)
    if not train_label_rows:
        raise ValueError("train_label_rows must not be empty")

    if relation_weights is None:
        train_end = max(train_label_rows) + 1
        relation_weights = compute_lagged_relation_weights(
            rows[:train_end], FEATURE_COLUMNS, lag_window
        )
    gates = build_trust_gates(relation_weights, target, gate_config)
    train_features, train_labels = build_trust_gated_features(
        rows, train_label_rows, gates, target, lag_window
    )
    coefficients = fit_linear_regression(train_features, train_labels)
    return TrustGatedModel(
        gates=gates,
        coefficients=tuple(coefficients),
        feature_names=tuple(trust_gated_feature_names(target, lag_window)),
    )


def predict_trust_gated(
    rows: Sequence[Row],
    label_rows: Iterable[int],
    model: TrustGatedModel,
    target: str = "target",
    lag_window: int = LAG_WINDOW,
) -> List[float]:
    features, _ = build_trust_gated_features(
        rows, label_rows, model.gates, target, lag_window
    )
    return predict_linear_regression(features, model.coefficients)


def build_trust_gated_features(
    rows: Sequence[Row],
    label_rows: Iterable[int],
    gates: Sequence[TrustGate],
    target: str = "target",
    lag_window: int = LAG_WINDOW,
) -> Tuple[List[List[float]], List[float]]:
    """Build target history plus one irreversible gated source mixture per lag."""
    features: List[List[float]] = []
    labels: List[float] = []
    for label_index in label_rows:
        sample = [1.0]
        for lag in range(1, lag_window + 1):
            history_row = rows[label_index - lag]
            sample.append(float(history_row[target]))
            sample.append(combine_gated_signals(history_row, gates))
        features.append(sample)
        labels.append(float(rows[label_index][target]))
    return features, labels


def trust_gated_feature_names(
    target: str = "target", lag_window: int = LAG_WINDOW
) -> List[str]:
    names = ["intercept"]
    for lag in range(1, lag_window + 1):
        names.append(f"{target}_lag{lag}")
        names.append(f"gated_relation_signal_lag{lag}")
    return names
