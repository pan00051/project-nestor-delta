"""Reusable train/validation parameter selection without test evaluation."""

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


@dataclass(frozen=True)
class AdaptiveCaseSpec:
    case_name: str
    csv_path: Path
    date_column: str
    target: str
    candidate_signals: Tuple[str, ...]
    train_start: str
    train_end: str
    validation_start: str
    validation_end: str
    test_start: str
    test_end: str
    relation_thresholds: Tuple[float, ...]
    lag_windows: Tuple[int, ...]
    max_selected_signals: Tuple[int, ...]
    output_dir: Path
    notes: str


@dataclass(frozen=True)
class ValidationGridRow:
    relation_threshold: float
    lag_window: int
    max_selected_signals: int
    candidate_count: int
    retained_after_threshold: Tuple[str, ...]
    admitted_after_cap: Tuple[str, ...]
    actual_ols_sources: Tuple[str, ...]
    dropped_collinear_sources: Tuple[str, ...]
    model_coefficients: Tuple[float, ...]
    fit_status: str
    validation_mae: float
    validation_rmse: float
    persistence_mae: float
    persistence_rmse: float
    mae_change_vs_persistence_pct: float
    train_label_count: int
    validation_label_count: int


@dataclass(frozen=True)
class ValidationSearchResult:
    rows: Tuple[ValidationGridRow, ...]
    selected: ValidationGridRow


REQUIRED_FIELDS = {
    "candidate_signals",
    "case_name",
    "csv",
    "date_column",
    "frequency",
    "lag_windows",
    "max_selected_signals",
    "notes",
    "output_dir",
    "relation_thresholds",
    "target",
    "test_end",
    "test_start",
    "train_end",
    "train_start",
    "validation_end",
    "validation_start",
}

OPTIONAL_FIELDS = {
    "transform_declarations",
}


def load_adaptive_case(path: Path) -> Tuple[AdaptiveCaseSpec, RealCaseData]:
    """Load a strict adaptive-case config and its aligned numeric CSV."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("adaptive case config must be a JSON object")
    missing = sorted(REQUIRED_FIELDS - set(payload))
    extra = sorted(set(payload) - REQUIRED_FIELDS - OPTIONAL_FIELDS)
    if missing:
        raise ValueError(f"adaptive case config missing fields: {missing}")
    if extra:
        raise ValueError(f"adaptive case config has unknown fields: {extra}")
    if payload["frequency"] != "monthly":
        raise ValueError("adaptive case frequency must be monthly")

    root = path.resolve().parent
    csv_path = Path(payload["csv"])
    if not csv_path.is_absolute():
        csv_path = root / csv_path
    output_dir = Path(payload["output_dir"])
    if not output_dir.is_absolute():
        output_dir = root / output_dir
    candidates = tuple(str(value) for value in payload["candidate_signals"])
    thresholds = tuple(float(value) for value in payload["relation_thresholds"])
    lag_windows = tuple(int(value) for value in payload["lag_windows"])
    max_signals = tuple(int(value) for value in payload["max_selected_signals"])
    spec = AdaptiveCaseSpec(
        case_name=str(payload["case_name"]),
        csv_path=csv_path,
        date_column=str(payload["date_column"]),
        target=str(payload["target"]),
        candidate_signals=candidates,
        train_start=str(payload["train_start"]),
        train_end=str(payload["train_end"]),
        validation_start=str(payload["validation_start"]),
        validation_end=str(payload["validation_end"]),
        test_start=str(payload["test_start"]),
        test_end=str(payload["test_end"]),
        relation_thresholds=thresholds,
        lag_windows=lag_windows,
        max_selected_signals=max_signals,
        output_dir=output_dir,
        notes=str(payload["notes"]),
    )
    _validate_spec(spec)
    return spec, _load_data(spec)


def run_validation_parameter_search(
    spec: AdaptiveCaseSpec, data: RealCaseData
) -> ValidationSearchResult:
    """Select parameters on validation only; never evaluate the declared test rows."""
    validation_rows = _window_rows(
        data.dates, spec.validation_start, spec.validation_end, 1
    )
    actuals = tuple(float(data.rows[index][spec.target]) for index in validation_rows)
    persistence = tuple(predict_persistence(data.rows, validation_rows, spec.target))
    persistence_mae = mae(actuals, persistence)
    persistence_rmse = rmse(actuals, persistence)
    train_start_index = data.dates.index(spec.train_start)
    train_end_index = data.dates.index(spec.train_end)
    variables = (spec.target,) + tuple(sorted(spec.candidate_signals))

    rows: List[ValidationGridRow] = []
    for lag_window in spec.lag_windows:
        train_label_rows = _window_rows(
            data.dates, spec.train_start, spec.train_end, lag_window
        )
        relation_rows = data.rows[train_start_index : train_end_index + 1]
        weights = compute_lagged_relation_weights(
            relation_rows, variables, lag_window
        )
        ranking = _stable_ranking(weights, spec.target)
        for threshold in spec.relation_thresholds:
            retained = tuple(weight for weight in ranking if weight.score > threshold)
            for max_signals in spec.max_selected_signals:
                admitted = retained[:max_signals]
                result = _evaluate_validation_combination(
                    spec,
                    data,
                    train_label_rows,
                    validation_rows,
                    actuals,
                    persistence,
                    persistence_mae,
                    persistence_rmse,
                    threshold,
                    lag_window,
                    max_signals,
                    ranking,
                    retained,
                    admitted,
                )
                rows.append(result)

    ordered = tuple(
        sorted(
            rows,
            key=lambda row: (
                row.relation_threshold,
                row.lag_window,
                row.max_selected_signals,
            ),
        )
    )
    selected = min(ordered, key=_selection_key)
    return ValidationSearchResult(rows=ordered, selected=selected)


def write_validation_search_reports(
    spec: AdaptiveCaseSpec, result: ValidationSearchResult
) -> Tuple[Path, Path]:
    """Write the full validation grid and selected parameters deterministically."""
    spec.output_dir.mkdir(parents=True, exist_ok=True)
    grid_path = spec.output_dir / "validation_parameter_grid.csv"
    selection_path = spec.output_dir / "validation_selection.json"
    fields = [
        "relation_threshold",
        "lag_window",
        "max_selected_signals",
        "candidate_count",
        "retained_after_threshold_count",
        "admitted_after_cap_count",
        "actual_ols_signal_count",
        "retained_after_threshold_sources",
        "admitted_after_cap_sources",
        "actual_ols_sources",
        "dropped_collinear_sources",
        "model_coefficients",
        "fit_status",
        "validation_mae",
        "validation_rmse",
        "persistence_mae",
        "persistence_rmse",
        "mae_change_vs_persistence_pct",
        "train_label_count",
        "validation_label_count",
        "test_evaluated",
    ]
    with grid_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in result.rows:
            writer.writerow(_grid_record(row))

    selected = result.selected
    baseline_guard_applied = selected.validation_mae >= selected.persistence_mae
    final_mode = "baseline_only" if baseline_guard_applied else "delta"
    payload = {
        "actual_ols_sources": (
            [] if baseline_guard_applied else list(selected.actual_ols_sources)
        ),
        "baseline_guard_applied": baseline_guard_applied,
        "best_delta_actual_ols_sources": list(selected.actual_ols_sources),
        "best_delta_fit_status": selected.fit_status,
        "best_delta_validation_mae": selected.validation_mae,
        "case_name": spec.case_name,
        "final_mode": final_mode,
        "fit_status": (
            "baseline_only_validation_guard"
            if baseline_guard_applied
            else selected.fit_status
        ),
        "lag_window": selected.lag_window,
        "mae_change_vs_persistence_pct": (
            0.0 if baseline_guard_applied else selected.mae_change_vs_persistence_pct
        ),
        "max_selected_signals": selected.max_selected_signals,
        "model_coefficients": (
            [] if baseline_guard_applied else list(selected.model_coefficients)
        ),
        "relation_threshold": selected.relation_threshold,
        "selection_rule": (
            "lowest validation MAE; ties prefer fewer actual OLS signals, higher "
            "threshold, shorter lag, lower max_selected_signals, then source names"
        ),
        "test_evaluated": False,
        "validation_mae": (
            selected.persistence_mae
            if baseline_guard_applied
            else selected.validation_mae
        ),
        "validation_persistence_mae": selected.persistence_mae,
    }
    selection_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return grid_path, selection_path


def _evaluate_validation_combination(
    spec: AdaptiveCaseSpec,
    data: RealCaseData,
    train_label_rows: Tuple[int, ...],
    validation_rows: Tuple[int, ...],
    actuals: Tuple[float, ...],
    persistence: Tuple[float, ...],
    persistence_mae: float,
    persistence_rmse: float,
    threshold: float,
    lag_window: int,
    max_signals: int,
    ranking: Tuple[RelationWeight, ...],
    retained: Tuple[RelationWeight, ...],
    admitted: Tuple[RelationWeight, ...],
) -> ValidationGridRow:
    if not admitted:
        selected: Tuple[RelationWeight, ...] = ()
        dropped: Tuple[str, ...] = ()
        coefficients: Tuple[float, ...] = ()
        fit_status = "baseline_only_no_retained_signal"
        predictions = persistence
    else:
        model = fit_real_case_predictor_with_backoff(
            data.rows,
            train_label_rows,
            admitted,
            spec.target,
            lag_window,
        )
        selected = model.selected_weights
        dropped = model.dropped_collinear_sources
        coefficients = model.coefficients
        fit_status = model.fit_status
        if fit_status == "baseline_only_no_stable_signal":
            predictions = persistence
        else:
            predictions = tuple(
                predict_real_case(
                    data.rows,
                    validation_rows,
                    model,
                    spec.target,
                    lag_window,
                )
            )
    validation_mae = mae(actuals, predictions)
    validation_rmse = rmse(actuals, predictions)
    return ValidationGridRow(
        relation_threshold=threshold,
        lag_window=lag_window,
        max_selected_signals=max_signals,
        candidate_count=len(ranking),
        retained_after_threshold=tuple(weight.source for weight in retained),
        admitted_after_cap=tuple(weight.source for weight in admitted),
        actual_ols_sources=tuple(weight.source for weight in selected),
        dropped_collinear_sources=dropped,
        model_coefficients=coefficients,
        fit_status=fit_status,
        validation_mae=validation_mae,
        validation_rmse=validation_rmse,
        persistence_mae=persistence_mae,
        persistence_rmse=persistence_rmse,
        mae_change_vs_persistence_pct=(validation_mae / persistence_mae - 1.0) * 100.0,
        train_label_count=len(train_label_rows),
        validation_label_count=len(validation_rows),
    )


def _selection_key(row: ValidationGridRow) -> Tuple[object, ...]:
    return (
        row.validation_mae,
        len(row.actual_ols_sources),
        -row.relation_threshold,
        row.lag_window,
        row.max_selected_signals,
        row.actual_ols_sources,
    )


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
        raise ValueError(f"window {start}..{end} has no label rows")
    return rows


def _validate_spec(spec: AdaptiveCaseSpec) -> None:
    if len(set(spec.candidate_signals)) != len(spec.candidate_signals):
        raise ValueError("adaptive candidate signals must be unique")
    if spec.target in spec.candidate_signals:
        raise ValueError("adaptive target must not be a candidate")
    if not (
        spec.train_start <= spec.train_end
        < spec.validation_start
        <= spec.validation_end
        < spec.test_start
        <= spec.test_end
    ):
        raise ValueError("adaptive train, validation, and test windows must not overlap")
    if not spec.relation_thresholds or any(
        not 0.0 <= value <= 1.0 for value in spec.relation_thresholds
    ):
        raise ValueError("relation thresholds must be between 0 and 1")
    if not spec.lag_windows or any(value < 1 for value in spec.lag_windows):
        raise ValueError("lag windows must be positive")
    if not spec.max_selected_signals or any(
        value < 1 or value > len(spec.candidate_signals)
        for value in spec.max_selected_signals
    ):
        raise ValueError("max selected signals are outside the candidate count")


def _load_data(spec: AdaptiveCaseSpec) -> RealCaseData:
    required = (spec.date_column, spec.target) + spec.candidate_signals
    rows: List[Mapping[str, float]] = []
    dates: List[str] = []
    with spec.csv_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None or set(reader.fieldnames) != set(required):
            raise ValueError("adaptive CSV columns must exactly match configured fields")
        for record in reader:
            date = str(record[spec.date_column])
            dates.append(date)
            rows.append(
                {
                    name: float(record[name])
                    for name in (spec.target,) + spec.candidate_signals
                }
            )
    if len(dates) != 168 or dates[0] != "2008-01" or dates[-1] != "2021-12":
        raise ValueError("adaptive CSV must cover exactly 2008-01..2021-12")
    for left, right in zip(dates, dates[1:]):
        left_year, left_month = (int(value) for value in left.split("-"))
        right_year, right_month = (int(value) for value in right.split("-"))
        if right_year * 12 + right_month != left_year * 12 + left_month + 1:
            raise ValueError("adaptive CSV dates must be contiguous monthly values")
    return RealCaseData(
        dates=tuple(dates),
        rows=tuple(rows),
        variables=(spec.target,) + tuple(sorted(spec.candidate_signals)),
    )


def _grid_record(row: ValidationGridRow) -> Dict[str, object]:
    return {
        "relation_threshold": f"{row.relation_threshold:.10f}",
        "lag_window": row.lag_window,
        "max_selected_signals": row.max_selected_signals,
        "candidate_count": row.candidate_count,
        "retained_after_threshold_count": len(row.retained_after_threshold),
        "admitted_after_cap_count": len(row.admitted_after_cap),
        "actual_ols_signal_count": len(row.actual_ols_sources),
        "retained_after_threshold_sources": ";".join(row.retained_after_threshold),
        "admitted_after_cap_sources": ";".join(row.admitted_after_cap),
        "actual_ols_sources": ";".join(row.actual_ols_sources),
        "dropped_collinear_sources": ";".join(row.dropped_collinear_sources),
        "model_coefficients": ";".join(
            f"{value:.10f}" for value in row.model_coefficients
        ),
        "fit_status": row.fit_status,
        "validation_mae": f"{row.validation_mae:.10f}",
        "validation_rmse": f"{row.validation_rmse:.10f}",
        "persistence_mae": f"{row.persistence_mae:.10f}",
        "persistence_rmse": f"{row.persistence_rmse:.10f}",
        "mae_change_vs_persistence_pct": f"{row.mae_change_vs_persistence_pct:.10f}",
        "train_label_count": row.train_label_count,
        "validation_label_count": row.validation_label_count,
        "test_evaluated": "false",
    }
