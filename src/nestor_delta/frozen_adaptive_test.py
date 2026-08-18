"""One-shot test evaluation for validation-frozen adaptive cases."""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

from .metrics import mae, rmse
from .real_case_analysis import (
    fit_real_case_predictor_with_backoff,
    predict_persistence,
    predict_real_case,
)
from .real_data import RealCaseData
from .relation_weights import (
    RelationWeight,
    compute_lagged_relation_weights,
    rank_target_sources,
)
from .validation_parameter_search import AdaptiveCaseSpec


@dataclass(frozen=True)
class FrozenAdaptiveSelection:
    case_name: str
    final_mode: str
    relation_threshold: float
    lag_window: int
    max_selected_signals: int
    baseline_guard_applied: bool


@dataclass(frozen=True)
class FrozenTestResult:
    fit_status: str
    selected_sources: Tuple[str, ...]
    dropped_collinear_sources: Tuple[str, ...]
    model_coefficients: Tuple[float, ...]
    persistence_mae: float
    persistence_rmse: float
    delta_mae: Optional[float]
    delta_rmse: Optional[float]
    mae_change_vs_persistence_pct: Optional[float]
    test_dates: Tuple[str, ...]
    actuals: Tuple[float, ...]
    persistence_predictions: Tuple[float, ...]
    delta_predictions: Tuple[Optional[float], ...]


def load_frozen_selection(path: Path) -> FrozenAdaptiveSelection:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("test_evaluated") is not False:
        raise ValueError("selection must be frozen before test evaluation")
    final_mode = str(payload["final_mode"])
    if final_mode not in {"baseline_only", "delta"}:
        raise ValueError("frozen final_mode must be baseline_only or delta")
    return FrozenAdaptiveSelection(
        case_name=str(payload["case_name"]),
        final_mode=final_mode,
        relation_threshold=float(payload["relation_threshold"]),
        lag_window=int(payload["lag_window"]),
        max_selected_signals=int(payload["max_selected_signals"]),
        baseline_guard_applied=bool(payload["baseline_guard_applied"]),
    )


def run_frozen_test_once(
    spec: AdaptiveCaseSpec,
    data: RealCaseData,
    selection: FrozenAdaptiveSelection,
) -> FrozenTestResult:
    """Refit on train+validation, then evaluate the declared test exactly once."""
    if selection.case_name != spec.case_name:
        raise ValueError("selection case_name does not match adaptive case")
    test_rows = _window_rows(data.dates, spec.test_start, spec.test_end, 1)
    actuals = tuple(float(data.rows[index][spec.target]) for index in test_rows)
    persistence = tuple(predict_persistence(data.rows, test_rows, spec.target))
    persistence_mae = mae(actuals, persistence)
    persistence_rmse = rmse(actuals, persistence)

    if selection.final_mode == "baseline_only":
        return FrozenTestResult(
            fit_status="baseline_only_validation_guard",
            selected_sources=(),
            dropped_collinear_sources=(),
            model_coefficients=(),
            persistence_mae=persistence_mae,
            persistence_rmse=persistence_rmse,
            delta_mae=None,
            delta_rmse=None,
            mae_change_vs_persistence_pct=None,
            test_dates=tuple(data.dates[index] for index in test_rows),
            actuals=actuals,
            persistence_predictions=persistence,
            delta_predictions=tuple(None for _ in test_rows),
        )

    lag_window = selection.lag_window
    fit_rows = _window_rows(
        data.dates, spec.train_start, spec.validation_end, lag_window
    )
    start_index = data.dates.index(spec.train_start)
    end_index = data.dates.index(spec.validation_end)
    variables = (spec.target,) + tuple(sorted(spec.candidate_signals))
    weights = compute_lagged_relation_weights(
        data.rows[start_index : end_index + 1], variables, lag_window
    )
    ranking = _stable_ranking(weights, spec.target)
    retained = tuple(
        weight for weight in ranking if weight.score > selection.relation_threshold
    )
    admitted = retained[: selection.max_selected_signals]
    if not admitted:
        return FrozenTestResult(
            fit_status="baseline_only_no_retained_signal_after_refit",
            selected_sources=(),
            dropped_collinear_sources=(),
            model_coefficients=(),
            persistence_mae=persistence_mae,
            persistence_rmse=persistence_rmse,
            delta_mae=None,
            delta_rmse=None,
            mae_change_vs_persistence_pct=None,
            test_dates=tuple(data.dates[index] for index in test_rows),
            actuals=actuals,
            persistence_predictions=persistence,
            delta_predictions=tuple(None for _ in test_rows),
        )
    model = fit_real_case_predictor_with_backoff(
        data.rows,
        fit_rows,
        admitted,
        spec.target,
        lag_window,
    )
    if model.fit_status == "baseline_only_no_stable_signal":
        return FrozenTestResult(
            fit_status=model.fit_status,
            selected_sources=(),
            dropped_collinear_sources=model.dropped_collinear_sources,
            model_coefficients=(),
            persistence_mae=persistence_mae,
            persistence_rmse=persistence_rmse,
            delta_mae=None,
            delta_rmse=None,
            mae_change_vs_persistence_pct=None,
            test_dates=tuple(data.dates[index] for index in test_rows),
            actuals=actuals,
            persistence_predictions=persistence,
            delta_predictions=tuple(None for _ in test_rows),
        )
    numeric_predictions = tuple(
        predict_real_case(data.rows, test_rows, model, spec.target, lag_window)
    )
    delta_mae = mae(actuals, numeric_predictions)
    delta_rmse = rmse(actuals, numeric_predictions)
    return FrozenTestResult(
        fit_status=model.fit_status,
        selected_sources=tuple(weight.source for weight in model.selected_weights),
        dropped_collinear_sources=model.dropped_collinear_sources,
        model_coefficients=model.coefficients,
        persistence_mae=persistence_mae,
        persistence_rmse=persistence_rmse,
        delta_mae=delta_mae,
        delta_rmse=delta_rmse,
        mae_change_vs_persistence_pct=(delta_mae / persistence_mae - 1.0) * 100.0,
        test_dates=tuple(data.dates[index] for index in test_rows),
        actuals=actuals,
        persistence_predictions=persistence,
        delta_predictions=tuple(numeric_predictions),
    )


def write_frozen_test_reports(
    output_dir: Path,
    spec: AdaptiveCaseSpec,
    selection: FrozenAdaptiveSelection,
    result: FrozenTestResult,
) -> Tuple[Path, Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    metrics_path = output_dir / "frozen_test_metrics.csv"
    predictions_path = output_dir / "frozen_test_predictions.csv"
    summary_path = output_dir / "frozen_test_summary.md"
    _write_metrics(metrics_path, spec, selection, result)
    _write_predictions(predictions_path, result)
    _write_summary(summary_path, spec, selection, result)
    return metrics_path, predictions_path, summary_path


def _write_metrics(
    path: Path,
    spec: AdaptiveCaseSpec,
    selection: FrozenAdaptiveSelection,
    result: FrozenTestResult,
) -> None:
    fields = [
        "case_name",
        "final_mode",
        "relation_threshold",
        "lag_window",
        "max_selected_signals",
        "actual_ols_signal_count",
        "actual_ols_sources",
        "dropped_collinear_sources",
        "fit_status",
        "persistence_mae",
        "persistence_rmse",
        "delta_mae",
        "delta_rmse",
        "mae_change_vs_persistence_pct",
        "test_sample_count",
        "parameters_adjusted_after_test",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerow(
            {
                "case_name": spec.case_name,
                "final_mode": selection.final_mode,
                "relation_threshold": f"{selection.relation_threshold:.10f}",
                "lag_window": selection.lag_window,
                "max_selected_signals": selection.max_selected_signals,
                "actual_ols_signal_count": len(result.selected_sources),
                "actual_ols_sources": ";".join(result.selected_sources),
                "dropped_collinear_sources": ";".join(
                    result.dropped_collinear_sources
                ),
                "fit_status": result.fit_status,
                "persistence_mae": f"{result.persistence_mae:.10f}",
                "persistence_rmse": f"{result.persistence_rmse:.10f}",
                "delta_mae": (
                    "" if result.delta_mae is None else f"{result.delta_mae:.10f}"
                ),
                "delta_rmse": (
                    "" if result.delta_rmse is None else f"{result.delta_rmse:.10f}"
                ),
                "mae_change_vs_persistence_pct": (
                    ""
                    if result.mae_change_vs_persistence_pct is None
                    else f"{result.mae_change_vs_persistence_pct:.10f}"
                ),
                "test_sample_count": len(result.test_dates),
                "parameters_adjusted_after_test": "false",
            }
        )


def _write_predictions(path: Path, result: FrozenTestResult) -> None:
    fields = ["date", "actual", "persistence", "delta_prediction"]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for date, actual, persistence, delta in zip(
            result.test_dates,
            result.actuals,
            result.persistence_predictions,
            result.delta_predictions,
        ):
            writer.writerow(
                {
                    "date": date,
                    "actual": f"{actual:.10f}",
                    "persistence": f"{persistence:.10f}",
                    "delta_prediction": "" if delta is None else f"{delta:.10f}",
                }
            )


def _write_summary(
    path: Path,
    spec: AdaptiveCaseSpec,
    selection: FrozenAdaptiveSelection,
    result: FrozenTestResult,
) -> None:
    delta_mae = "n/a" if result.delta_mae is None else f"{result.delta_mae:.6f}"
    change = (
        "n/a"
        if result.mae_change_vs_persistence_pct is None
        else f"{result.mae_change_vs_persistence_pct:+.2f}%"
    )
    lines = [
        f"# Frozen Test Result: {spec.case_name}",
        "",
        "Parameters were selected using validation only and were not adjusted after test.",
        (
            "The Delta model was refit on train plus validation before one test evaluation."
            if selection.final_mode == "delta"
            else "Baseline-only mode was frozen from validation before one test evaluation."
        ),
        "Results describe predictive usefulness and co-movement, not causality.",
        "",
        f"- Final mode: `{selection.final_mode}`",
        f"- Relation threshold: `{selection.relation_threshold:.2f}`",
        f"- Lag window: `{selection.lag_window}`",
        f"- Maximum selected signals: `{selection.max_selected_signals}`",
        f"- Actual OLS sources: `{';'.join(result.selected_sources)}`",
        f"- Fit status: `{result.fit_status}`",
        f"- Test persistence MAE: `{result.persistence_mae:.6f}`",
        f"- Test Delta MAE: `{delta_mae}`",
        f"- MAE change vs persistence: `{change}`",
        f"- Test samples: `{len(result.test_dates)}`",
        "- Parameters adjusted after test: `false`",
        "",
    ]
    if selection.final_mode == "baseline_only":
        lines.extend(
            [
                "The validation baseline guard selected persistence before test. No Delta",
                "model or Delta metric is fabricated for this case.",
                "",
            ]
        )
    path.write_text("\n".join(lines), encoding="utf-8")


def _stable_ranking(
    weights: Sequence[RelationWeight], target: str
) -> Tuple[RelationWeight, ...]:
    return tuple(
        sorted(
            rank_target_sources(weights, target),
            key=lambda weight: (-weight.score, weight.source, weight.lag),
        )
    )


def _window_rows(
    dates: Tuple[str, ...], start: str, end: str, lag_window: int
) -> Tuple[int, ...]:
    rows = tuple(
        index
        for index, date in enumerate(dates)
        if index >= lag_window and start <= date <= end
    )
    if not rows:
        raise ValueError(f"window {start}..{end} has no rows")
    return rows
