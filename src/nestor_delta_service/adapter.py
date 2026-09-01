"""Report JSON v1 adapter over the existing Delta pipeline."""

from __future__ import annotations

import base64
import csv
import hashlib
import io
import json
from dataclasses import dataclass
from pathlib import Path
from statistics import mean
from typing import Any, Mapping, Sequence
from urllib.parse import parse_qsl

from nestor_delta.dynamic_weights import (
    compute_rolling_transformed_relation_weights,
    target_source_trajectory,
)
from nestor_delta.evidence_gate import EvidenceGateResult, select_relations_with_evidence
from nestor_delta.noise_floor import correlation_noise_floor
from nestor_delta.prediction_confidence import compute_prediction_confidence
from nestor_delta.real_case_analysis import predict_persistence
from nestor_delta.real_data import (
    load_real_case_config,
    load_real_case_data,
)
from nestor_delta.relation_weights import RelationWeight, rank_target_sources
from nestor_delta.stationarity import (
    PERSISTENCE_ACF_THRESHOLD,
    compute_transformed_relation_weights,
    signal_diagnostics,
    validate_transform_declarations,
)
from nestor_delta.temporal_stability import classify_relation_lifecycle

from .eurostat import build_eurostat_snapshot
from .errors import SCHEMA_VERSION, ServiceError, analysis_failure, not_found, validation_error
from .versioning import PIPELINE_VERSION

REPO_ROOT = Path(__file__).resolve().parents[2]
EVIDENCE_GATE_CONFIG = {
    "alpha": 0.05,
    "min_stability": 0.45,
    "max_uncertainty": 0.20,
    "min_sample_support": 0.50,
}
SUPPORTED_CASES = {
    "synthetic_ground_truth_calibration_control": REPO_ROOT
    / "cases"
    / "synthetic_ground_truth_calibration_control"
    / "case.json",
    "spain_retail_eurostat_2008_2025": REPO_ROOT
    / "cases"
    / "spain_retail_eurostat_2008_2025"
    / "case.json",
    "spain_retail_eurostat_expanded_2008_2025": REPO_ROOT
    / "cases"
    / "spain_retail_eurostat_expanded_2008_2025"
    / "case.json",
    "spain_industrial_production_eurostat_2008_2023": REPO_ROOT
    / "cases"
    / "spain_industrial_production_eurostat_2008_2023"
    / "case.json",
}


@dataclass(frozen=True)
class AnalysisInput:
    case_name: str
    dates: tuple[str, ...]
    rows: tuple[Mapping[str, float], ...]
    target: str
    candidate_signals: tuple[str, ...]
    transform_declarations: Mapping[str, str]
    train_end: str
    lag_window: int
    source: str
    signal_metadata: Mapping[str, Mapping[str, Any]]
    snapshot_hash: str | None = None
    provenance: Mapping[str, Any] | None = None
    snapshot_csv_text: str | None = None
    snapshot_columns: tuple[str, ...] | None = None
    baseline_test_start: str | None = None

    @property
    def variables(self) -> tuple[str, ...]:
        return (self.target,) + tuple(sorted(self.candidate_signals))


def analyze_payload(payload: Mapping[str, Any]) -> tuple[int, dict[str, Any]]:
    """Run W1 synchronous analysis and return ``(http_status, report)``."""
    try:
        analysis_input = _payload_to_input(payload)
        return 200, build_report(analysis_input)
    except ServiceError as exc:
        return exc.http_status, exc.to_report()
    except ValueError as exc:
        error = validation_error(
            "invalid_input", str(exc), detail={"exception": type(exc).__name__}
        )
        return error.http_status, error.to_report()
    except Exception as exc:  # pragma: no cover - defensive API boundary
        error = analysis_failure(
            "internal_error", str(exc), detail={"exception": type(exc).__name__}
        )
        return error.http_status, error.to_report()


def audit_payload(payload: Mapping[str, Any]) -> tuple[int, dict[str, Any]]:
    """Run the W2 dry-run audit without relation scoring or gate selection."""
    try:
        analysis_input = _payload_to_input(payload)
        audit = _audit_blocks(analysis_input)
        return 200, {
            "schema_version": SCHEMA_VERSION,
            "outcome": "ok_to_analyze",
            "snapshot": _snapshot_block(analysis_input),
            "data_audit": audit["data_audit"],
            "transform_diagnostics": audit["transform_diagnostics"],
        }
    except ServiceError as exc:
        return exc.http_status, exc.to_report()
    except ValueError as exc:
        error = validation_error(
            "invalid_input", str(exc), detail={"exception": type(exc).__name__}
        )
        return error.http_status, error.to_report()
    except Exception as exc:  # pragma: no cover - defensive API boundary
        error = analysis_failure(
            "internal_error", str(exc), detail={"exception": type(exc).__name__}
        )
        return error.http_status, error.to_report()


def snapshot_payload(payload: Mapping[str, Any]) -> tuple[int, dict[str, Any]]:
    """Prepare a frozen CSV snapshot without running audit or analysis."""
    try:
        analysis_input = _payload_to_input(payload)
        csv_text = analysis_input.snapshot_csv_text or _analysis_input_csv(analysis_input)
        return 200, {
            "schema_version": SCHEMA_VERSION,
            "outcome": "snapshot_ready",
            "snapshot": _snapshot_block(analysis_input),
            "csv_base64": base64.b64encode(csv_text.encode("utf-8")).decode("ascii"),
            "columns": list(
                analysis_input.snapshot_columns or ["date", *analysis_input.variables]
            ),
            "row_count": len(analysis_input.rows),
        }
    except ServiceError as exc:
        return exc.http_status, exc.to_report()
    except ValueError as exc:
        error = validation_error(
            "invalid_input", str(exc), detail={"exception": type(exc).__name__}
        )
        return error.http_status, error.to_report()
    except Exception as exc:  # pragma: no cover - defensive API boundary
        error = analysis_failure(
            "internal_error", str(exc), detail={"exception": type(exc).__name__}
        )
        return error.http_status, error.to_report()


def build_report(analysis_input: AnalysisInput) -> dict[str, Any]:
    """Compose existing S7-S10 capabilities into Report JSON v1."""
    audit = _audit_blocks(analysis_input)
    train_rows = _train_rows(analysis_input)
    transforms = _validate_transforms(analysis_input)
    weights = compute_transformed_relation_weights(
        train_rows,
        analysis_input.variables,
        analysis_input.lag_window,
        transforms,
    )
    ranking = rank_target_sources(weights, analysis_input.target)
    relation_views, relation_objects = _relation_views(analysis_input, train_rows, ranking)
    gate = select_relations_with_evidence(
        relation_objects,
        max_lag=analysis_input.lag_window,
        target=analysis_input.target,
        **EVIDENCE_GATE_CONFIG,
    )
    relation_views = _apply_gate_decisions(relation_views, gate)
    outcome = "ok" if gate.selected_relations else "baseline_only"

    return {
        "schema_version": SCHEMA_VERSION,
        "producer": "nestor-delta",
        "pipeline_version": PIPELINE_VERSION,
        "outcome": outcome,
        "generated_as_of": analysis_input.train_end,
        "case": {
            "name": analysis_input.case_name,
            "target": analysis_input.target,
            "candidate_signals": list(analysis_input.candidate_signals),
            "frequency": "monthly",
            "n_observations": len(analysis_input.rows),
            "train_end": analysis_input.train_end,
            "lag_window": analysis_input.lag_window,
        },
        "snapshot": _snapshot_block(analysis_input),
        "configuration": _configuration_block(
            analysis_input, train_rows, relation_objects
        ),
        "transform_declarations": dict(transforms),
        "transform_diagnostics": audit["transform_diagnostics"],
        "data_audit": audit["data_audit"],
        "baseline": _baseline_block(analysis_input),
        "evaluation": None,
        "noise_floor": _noise_floor_block(
            relation_objects, analysis_input.lag_window, len(analysis_input.candidate_signals)
        ),
        "relations": relation_views,
        "selection": {
            "fit_status": gate.fit_status,
            "final_mode": "not_evaluated",
            "selected_count": len(gate.selected_relations),
            "selected_sources": [relation.source for relation in gate.selected_relations],
        },
        "prediction_confidence": _prediction_confidence_block(gate),
        "narrative": _narrative(outcome, gate, len(relation_views)),
        "warnings": _report_warnings(analysis_input, train_rows),
    }


def _payload_to_input(payload: Mapping[str, Any]) -> AnalysisInput:
    case_name = payload.get("case_name")
    csv_base64 = payload.get("csv_base64")
    eurostat = payload.get("eurostat")
    source_count = sum(1 for source in (case_name, csv_base64, eurostat) if bool(source))
    if source_count != 1:
        raise validation_error(
            "invalid_source",
            "Exactly one of case_name, csv_base64, or eurostat must be provided.",
            field="case_name",
        )
    if case_name:
        return _case_input(str(case_name), payload)
    if eurostat:
        if not isinstance(eurostat, Mapping):
            raise validation_error(
                "invalid_eurostat_request",
                "eurostat must be an object.",
                field="eurostat",
            )
        return _eurostat_input(eurostat, payload)
    return _upload_input(str(csv_base64), payload)


def _snapshot_block(analysis_input: AnalysisInput) -> dict[str, Any]:
    return {
        "hash": analysis_input.snapshot_hash,
        "source": analysis_input.source,
        "provenance": analysis_input.provenance,
    }


def _analysis_input_csv(analysis_input: AnalysisInput) -> str:
    handle = io.StringIO()
    fieldnames = ["date", *analysis_input.variables]
    writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()
    for date, row in zip(analysis_input.dates, analysis_input.rows):
        writer.writerow(
            {
                "date": date,
                **{
                    signal: f"{float(row[signal]):.10f}"
                    for signal in analysis_input.variables
                },
            }
        )
    return handle.getvalue()


def _case_input(case_name: str, payload: Mapping[str, Any]) -> AnalysisInput:
    config_path = SUPPORTED_CASES.get(case_name)
    if config_path is None:
        raise not_found(
            "case_not_found",
            f"Case {case_name!r} was not found.",
            field="case_name",
            detail={"case_name": case_name},
        )
    config = load_real_case_config(config_path)
    data = load_real_case_data(config)
    transforms = payload.get("transform_declarations") or config.transform_declarations
    if transforms is None:
        raise validation_error(
            "undeclared_transform",
            "transform_declarations are required for every signal and target.",
            field="transform_declarations",
        )
    candidates = tuple(payload.get("candidate_signals") or config.candidate_signals)
    if not candidates:
        raise validation_error(
            "missing_candidate_signals",
            "candidate_signals must include at least one signal.",
            field="candidate_signals",
        )
    return AnalysisInput(
        case_name=config.case_name,
        dates=data.dates,
        rows=data.rows,
        target=str(payload.get("target") or config.target),
        candidate_signals=candidates,
        transform_declarations=transforms,
        train_end=str(payload.get("train_end") or config.train_end),
        lag_window=int(payload.get("lag_window") or config.lag_window),
        source="case",
        signal_metadata=_case_signal_metadata(config_path, data.dates),
        snapshot_hash=_file_sha256(config.csv_path),
        provenance=_case_provenance(config_path),
        snapshot_csv_text=config.csv_path.read_text(encoding="utf-8"),
        snapshot_columns=(config.date_column, config.target, *candidates),
        baseline_test_start=config.test_start,
    )


def _upload_input(csv_base64: str, payload: Mapping[str, Any]) -> AnalysisInput:
    required = ("target", "candidate_signals", "transform_declarations", "train_end", "lag_window")
    missing = [field for field in required if field not in payload]
    if missing:
        raise validation_error(
            "missing_request_field",
            f"Missing required request fields: {missing}",
            detail={"missing": missing},
        )
    candidates = tuple(str(item) for item in payload["candidate_signals"])
    if not candidates:
        raise validation_error(
            "missing_candidate_signals",
            "candidate_signals must include at least one signal.",
            field="candidate_signals",
        )
    date_column = str(payload.get("date_column") or "date")
    try:
        csv_bytes = base64.b64decode(csv_base64, validate=True)
    except Exception as exc:
        raise validation_error(
            "invalid_csv_base64",
            "The uploaded CSV could not be read. Upload a valid monthly CSV file.",
            field="csv_base64",
            detail={"exception": type(exc).__name__},
        ) from exc
    if _looks_like_image(csv_bytes):
        raise validation_error(
            "invalid_csv_file_type",
            "This file does not look like a CSV (it appears to be an image). "
            "Upload a monthly CSV instead.",
            field="csv_base64",
            detail={"detected_type": "image"},
        )
    try:
        decoded = csv_bytes.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise validation_error(
            "invalid_csv_encoding",
            "This file is not UTF-8 encoded. Re-save it as CSV UTF-8 "
            "(Excel: Save As -> CSV UTF-8) and upload again.",
            field="csv_base64",
            detail={"exception": type(exc).__name__},
        ) from exc
    dates, rows = _read_csv_snapshot(
        decoded,
        date_column,
        str(payload["target"]),
        candidates,
    )
    return AnalysisInput(
        case_name=str(payload.get("case_name") or "uploaded_snapshot"),
        dates=dates,
        rows=rows,
        target=str(payload["target"]),
        candidate_signals=candidates,
        transform_declarations=payload["transform_declarations"],
        train_end=str(payload["train_end"]),
        lag_window=int(payload["lag_window"]),
        source="upload",
        signal_metadata={},
        snapshot_hash=_text_sha256(decoded),
        provenance=None,
        snapshot_csv_text=decoded,
        snapshot_columns=(date_column, str(payload["target"]), *candidates),
    )


def _eurostat_input(
    eurostat_payload: Mapping[str, Any],
    payload: Mapping[str, Any],
) -> AnalysisInput:
    required = ("target", "candidate_signals", "transform_declarations", "train_end", "lag_window")
    missing = [field for field in required if field not in payload]
    if missing:
        raise validation_error(
            "missing_request_field",
            f"Missing required request fields: {missing}",
            detail={"missing": missing},
        )
    try:
        snapshot = build_eurostat_snapshot(eurostat_payload)
    except ValueError as exc:
        raise validation_error(
            "invalid_eurostat_request",
            str(exc),
            field="eurostat",
        ) from exc
    target = str(payload["target"])
    candidates = tuple(str(item) for item in payload["candidate_signals"])
    available = set(snapshot.rows[0]) if snapshot.rows else set()
    missing_signals = sorted({target, *candidates} - available)
    if missing_signals:
        raise validation_error(
            "unknown_signal",
            f"Eurostat snapshot is missing requested signals: {missing_signals}",
            field="eurostat.series",
            detail={"missing_signals": missing_signals},
        )
    return AnalysisInput(
        case_name=str(payload.get("case_name") or "eurostat_snapshot"),
        dates=snapshot.dates,
        rows=snapshot.rows,
        target=target,
        candidate_signals=candidates,
        transform_declarations=payload["transform_declarations"],
        train_end=str(payload["train_end"]),
        lag_window=int(payload["lag_window"]),
        source="eurostat",
        signal_metadata=snapshot.signal_metadata,
        snapshot_hash=snapshot.snapshot_hash,
        provenance=snapshot.provenance,
        snapshot_csv_text=snapshot.csv_text,
        snapshot_columns=tuple(snapshot.csv_text.splitlines()[0].split(",")),
    )


def _read_csv_snapshot(
    text: str,
    date_column: str,
    target: str,
    candidate_signals: tuple[str, ...],
) -> tuple[tuple[str, ...], tuple[Mapping[str, float], ...]]:
    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None:
        raise validation_error("empty_csv", "CSV must include a header row.", field="csv_base64")
    required = (date_column, target) + candidate_signals
    missing = [column for column in required if column not in reader.fieldnames]
    if missing:
        raise validation_error(
            "unknown_signal",
            f"CSV is missing required columns: {missing}",
            field="csv_base64",
            detail={"missing_columns": missing},
        )
    dates = []
    rows = []
    for row_index, record in enumerate(reader, start=2):
        date = str(record[date_column]).strip()
        _parse_month(date, f"CSV row {row_index} date")
        numeric = {}
        for column in (target,) + candidate_signals:
            try:
                numeric[column] = float(record[column])
            except ValueError as exc:
                raise validation_error(
                    "non_numeric_value",
                    f"Non-numeric value in column {column!r} at CSV row {row_index}.",
                    field="csv_base64",
                ) from exc
        dates.append(date)
        rows.append(numeric)
    return tuple(dates), tuple(rows)


def _looks_like_image(content: bytes) -> bool:
    image_signatures = (
        b"\x89PNG\r\n\x1a\n",
        b"\xff\xd8\xff",
        b"GIF87a",
        b"GIF89a",
        b"BM",
        b"RIFF",
    )
    return any(content.startswith(signature) for signature in image_signatures)


def _validate_transforms(analysis_input: AnalysisInput) -> Mapping[str, str]:
    try:
        return validate_transform_declarations(
            analysis_input.variables, analysis_input.transform_declarations
        )
    except ValueError as exc:
        raise validation_error(
            "undeclared_transform",
            str(exc),
            field="transform_declarations",
        ) from exc


def _train_rows(analysis_input: AnalysisInput) -> tuple[Mapping[str, float], ...]:
    rows = tuple(
        row
        for date, row in zip(analysis_input.dates, analysis_input.rows)
        if date <= analysis_input.train_end
    )
    if len(rows) <= analysis_input.lag_window:
        raise validation_error(
            "too_few_observations",
            "Train window must contain more rows than lag_window.",
            field="train_end",
        )
    return rows


def _date_axis_audit(dates: tuple[str, ...]) -> dict[str, Any]:
    if not dates:
        return {
            "continuous": False,
            "expected_months": 0,
            "present": 0,
            "missing_months": [],
            "duplicate_months": [],
        }
    duplicate_months = sorted(date for date in set(dates) if dates.count(date) > 1)
    start = _parse_month(dates[0], "first date")
    end = _parse_month(dates[-1], "last date")
    expected_months = max(0, end - start + 1)
    expected = [_month_label(index) for index in range(start, end + 1)]
    present_set = set(dates)
    missing_months = [date for date in expected if date not in present_set]
    continuous = not duplicate_months and tuple(expected) == dates
    return {
        "continuous": continuous,
        "expected_months": expected_months,
        "present": len(dates),
        "missing_months": missing_months,
        "duplicate_months": duplicate_months,
    }


def _signal_audit(analysis_input: AnalysisInput) -> list[dict[str, Any]]:
    train_rows = tuple(
        row
        for date, row in zip(analysis_input.dates, analysis_input.rows)
        if date <= analysis_input.train_end
    )
    output = []
    diagnostics_by_signal = {}
    if len(train_rows) >= 2:
        diagnostics_by_signal = {
            diagnostic.signal: diagnostic
            for diagnostic in signal_diagnostics(train_rows, analysis_input.variables)
        }
    for signal in analysis_input.variables:
        metadata = analysis_input.signal_metadata.get(signal, {})
        diagnostic = diagnostics_by_signal.get(signal)
        output.append(
            {
                "signal": signal,
                "sample_count": sum(1 for row in analysis_input.rows if signal in row),
                "unit": metadata.get("unit", "unknown"),
                "seasonal_adjustment": metadata.get("seasonal_adjustment", "unknown"),
                "coverage": metadata.get(
                    "coverage",
                    {
                        "start": analysis_input.dates[0] if analysis_input.dates else None,
                        "end": analysis_input.dates[-1] if analysis_input.dates else None,
                        "months": len(analysis_input.dates),
                    },
                ),
                "lag1_acf": None if diagnostic is None else diagnostic.level_lag1_acf,
                "highly_persistent_risk": (
                    False if diagnostic is None else diagnostic.highly_persistent_risk
                ),
            }
        )
    return output


def _audit_blocks(analysis_input: AnalysisInput) -> dict[str, Any]:
    date_axis = _date_axis_audit(analysis_input.dates)
    data_audit = {
        "date_axis": date_axis,
        "signals": _signal_audit(analysis_input),
        "candidate_pool_available": bool(analysis_input.candidate_signals),
    }
    if not analysis_input.dates:
        raise validation_error(
            "too_few_observations",
            "CSV must include at least one data row.",
            field="csv_base64",
            report_fields={"data_audit": data_audit, "transform_diagnostics": []},
        )
    if date_axis["duplicate_months"]:
        duplicates = date_axis["duplicate_months"]
        shown = ", ".join(duplicates[:5])
        suffix = f" ({len(duplicates)} duplicate months total)" if len(duplicates) > 5 else ""
        raise validation_error(
            "duplicate_month",
            f"CSV has duplicate months: {shown}{suffix}. Keep one row per month and upload again.",
            field="csv_base64",
            detail={"duplicate_months": date_axis["duplicate_months"]},
            report_fields={"data_audit": data_audit, "transform_diagnostics": []},
        )
    if not date_axis["continuous"]:
        missing = date_axis["missing_months"]
        message = (
            f"Month {missing[0]} is missing; add the missing row and upload again."
            if missing
            else "CSV dates must be contiguous and sorted monthly."
        )
        raise validation_error(
            "non_contiguous_dates",
            message,
            field="csv_base64",
            detail={"missing_months": missing},
            report_fields={"data_audit": data_audit, "transform_diagnostics": []},
        )

    train_rows = _train_rows(analysis_input)
    transforms = _validate_transforms(analysis_input)
    diagnostics = _transform_diagnostics(train_rows, analysis_input.variables, transforms)
    rejected = [item for item in diagnostics if item["verdict"] == "rejected"]
    if rejected:
        first = rejected[0]
        raise validation_error(
            "high_persistence_requires_transform",
            (
                f"Signal {first['signal']!r} has lag-1 ACF "
                f"{first['lag1_acf']:.3f} but was declared 'none'."
            ),
            field="transform_declarations",
            detail={
                "signals": [item["signal"] for item in rejected],
                "threshold": PERSISTENCE_ACF_THRESHOLD,
            },
            report_fields={
                "data_audit": data_audit,
                "transform_diagnostics": diagnostics,
            },
        )
    return {"data_audit": data_audit, "transform_diagnostics": diagnostics}


def _case_signal_metadata(
    config_path: Path,
    dates: Sequence[str],
) -> Mapping[str, Mapping[str, Any]]:
    manifest_path = config_path.parent / "source_manifest.json"
    if not manifest_path.exists():
        return {}
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    coverage = manifest.get("coverage")
    if not isinstance(coverage, dict):
        coverage = {
            "start": dates[0] if dates else None,
            "end": dates[-1] if dates else None,
            "months": len(dates),
        }
    metadata = {}
    for item in manifest.get("series", []):
        if not isinstance(item, dict) or "name" not in item:
            continue
        scope = _manifest_scope(item)
        metadata[str(item["name"])] = {
            "unit": scope.get("unit", "unknown"),
            "seasonal_adjustment": scope.get("s_adj", "unknown"),
            "coverage": coverage,
        }
    return metadata


def _manifest_scope(item: Mapping[str, Any]) -> Mapping[str, str]:
    raw = str(item.get("filters") or item.get("actual_scope") or "")
    if "&" in raw and "=" in raw:
        return {key: value for key, value in parse_qsl(raw)}
    scope = {}
    for part in raw.split(";"):
        if "=" not in part:
            continue
        key, value = part.split("=", 1)
        scope[key.strip()] = value.strip()
    return scope


def _case_provenance(config_path: Path) -> Mapping[str, Any] | None:
    manifest_path = config_path.parent / "source_manifest.json"
    if not manifest_path.exists():
        return None
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    if not isinstance(manifest, Mapping):
        return None
    return manifest


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _text_sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _transform_diagnostics(
    rows: Sequence[Mapping[str, float]],
    variables: Sequence[str],
    transforms: Mapping[str, str],
) -> list[dict[str, Any]]:
    output = []
    for diagnostic in signal_diagnostics(rows, variables, transforms):
        declared = transforms[diagnostic.signal]
        rejected = diagnostic.highly_persistent_risk and declared == "none"
        output.append(
            {
                "signal": diagnostic.signal,
                "declared": declared,
                "lag1_acf": diagnostic.level_lag1_acf,
                "highly_persistent_risk": diagnostic.highly_persistent_risk,
                "verdict": "rejected" if rejected else "accepted",
            }
        )
    return output


def _relation_views(
    analysis_input: AnalysisInput,
    train_rows: Sequence[Mapping[str, float]],
    ranking: Sequence[RelationWeight],
) -> tuple[list[dict[str, Any]], list[RelationWeight]]:
    relation_objects = _s9_relation_objects(analysis_input, train_rows, ranking)
    reference = max(relation.sample_count for relation in relation_objects)
    pair_count = max(1, len(relation_objects))
    views = []
    for relation in relation_objects:
        floor = correlation_noise_floor(
            relation.sample_count,
            comparisons=analysis_input.lag_window * pair_count,
        )
        views.append(
            {
                "source": relation.source,
                "target": relation.target,
                "lag": relation.lag,
                "transform": relation.transform,
                "effect": {
                    "score": relation.score,
                    "weight": relation.weight,
                    "sign": _sign(relation.weight),
                    "noise_floor": floor.threshold,
                    "effect_size_vs_noise_floor": (
                        relation.score / floor.threshold if floor.threshold else None
                    ),
                },
                "significance": {"p_value": None, "fdr_threshold": None, "clears": None},
                "stability": relation.stability,
                "uncertainty": relation.uncertainty,
                "sample_support": min(1.0, relation.sample_count / reference),
                "lifecycle": _lifecycle_block(analysis_input, train_rows, relation.source),
                "selected": None,
                "reason_code": "not_selected",
                "reason_text": "",
                "trajectory": _trajectory_block(
                    analysis_input, train_rows, relation.source
                ),
            }
        )
    return views, relation_objects


def _s9_relation_objects(
    analysis_input: AnalysisInput,
    train_rows: Sequence[Mapping[str, float]],
    ranking: Sequence[RelationWeight],
) -> list[RelationWeight]:
    if not _rolling_lifecycle_available(analysis_input, train_rows):
        return list(ranking)
    window_size = _rolling_window_size(analysis_input, train_rows)
    if window_size <= analysis_input.lag_window:
        return list(ranking)
    steps = range(window_size + analysis_input.lag_window + 1, len(train_rows) + 1, 6)
    try:
        rolling = compute_rolling_transformed_relation_weights(
            train_rows,
            analysis_input.variables,
            analysis_input.lag_window,
            steps,
            window_size,
            analysis_input.transform_declarations,
        )
    except ValueError:
        return list(ranking)
    by_source = {}
    for relation in ranking:
        trajectory = target_source_trajectory(rolling, analysis_input.target, relation.source)
        lifecycle = classify_relation_lifecycle(
            trajectory,
            min_stability=EVIDENCE_GATE_CONFIG["min_stability"],
        )
        by_source[relation.source] = RelationWeight(
            source=relation.source,
            target=relation.target,
            lag=relation.lag,
            weight=relation.weight,
            score=relation.score,
            sample_count=relation.sample_count,
            transform=relation.transform,
            stability=lifecycle.relation.stability,
            uncertainty=lifecycle.relation.uncertainty,
            selected=relation.selected,
        )
    return [by_source.get(relation.source, relation) for relation in ranking]


def _lifecycle_block(
    analysis_input: AnalysisInput,
    train_rows: Sequence[Mapping[str, float]],
    source: str,
) -> dict[str, Any]:
    if not _rolling_lifecycle_available(analysis_input, train_rows):
        return {"state": "insufficient_evidence", "points": None}
    window_size = _rolling_window_size(analysis_input, train_rows)
    steps = range(window_size + analysis_input.lag_window + 1, len(train_rows) + 1, 6)
    try:
        rolling = compute_rolling_transformed_relation_weights(
            train_rows,
            analysis_input.variables,
            analysis_input.lag_window,
            steps,
            window_size,
            analysis_input.transform_declarations,
        )
        lifecycle = classify_relation_lifecycle(
            target_source_trajectory(rolling, analysis_input.target, source),
            min_stability=EVIDENCE_GATE_CONFIG["min_stability"],
        )
        return {"state": lifecycle.state, "points": lifecycle.points}
    except ValueError:
        return {"state": "insufficient_evidence", "points": None}


def _trajectory_block(
    analysis_input: AnalysisInput,
    train_rows: Sequence[Mapping[str, float]],
    source: str,
) -> list[dict[str, Any]] | None:
    if not _rolling_lifecycle_available(analysis_input, train_rows):
        return None
    window_size = _rolling_window_size(analysis_input, train_rows)
    steps = range(window_size + analysis_input.lag_window + 1, len(train_rows) + 1, 6)
    try:
        rolling = compute_rolling_transformed_relation_weights(
            train_rows,
            analysis_input.variables,
            analysis_input.lag_window,
            steps,
            window_size,
            analysis_input.transform_declarations,
        )
        trajectory = target_source_trajectory(rolling, analysis_input.target, source)
    except ValueError:
        return None
    if not trajectory:
        return None
    return [
        {
            "step": point.step,
            "date": analysis_input.dates[min(point.step - 1, len(analysis_input.dates) - 1)],
            "score": point.score,
            "sign": _sign(point.weight),
            "lag": point.lag,
        }
        for point in trajectory
    ]


def _configuration_block(
    analysis_input: AnalysisInput,
    train_rows: Sequence[Mapping[str, float]],
    relation_objects: Sequence[RelationWeight],
) -> dict[str, Any]:
    relation_sample_count = (
        max(relation.sample_count for relation in relation_objects)
        if relation_objects
        else 0
    )
    comparisons = max(
        1, analysis_input.lag_window * len(analysis_input.candidate_signals)
    )
    return {
        "reproducibility": {
            "rule": (
                "effective configuration is derived from snapshot, analysis "
                "params, and pipeline_version; same three inputs -> same report"
            )
        },
        "inputs": {
            "source": analysis_input.source,
            "train_end": analysis_input.train_end,
            "lag_window": analysis_input.lag_window,
            "candidate_count": len(analysis_input.candidate_signals),
            "train_observations": len(train_rows),
            "transform_declarations": dict(analysis_input.transform_declarations),
        },
        "effect": {
            "score_scope": "full_train_window",
            "ranking": "score_descending_then_source",
        },
        "rolling_lifecycle": {
            "window_rule": "min(36, max(lag_window + 6, train_observations // 3))",
            "effective_window": (
                _rolling_window_size(analysis_input, train_rows)
                if _rolling_lifecycle_available(analysis_input, train_rows)
                else None
            ),
            "step_interval": 6,
            "state_rule": "S9 end-of-sample trajectory classifier",
        },
        "noise_floor": {
            "role": "diagnostic_not_gate",
            "sample_count": relation_sample_count,
            "comparisons_rule": "lag_window * candidate_count",
            "comparisons": comparisons,
            "alpha": EVIDENCE_GATE_CONFIG["alpha"],
        },
        "evidence_gate": {
            "selection_terms": [
                "FDR",
                "stability",
                "uncertainty",
                "sample_support",
            ],
            **EVIDENCE_GATE_CONFIG,
        },
    }


def _rolling_window_size(
    analysis_input: AnalysisInput,
    train_rows: Sequence[Mapping[str, float]],
) -> int:
    return min(36, max(analysis_input.lag_window + 6, len(train_rows) // 3))


def _rolling_lifecycle_min_observations(lag_window: int) -> int:
    # Let n be train observations and L be lag_window. The established
    # non-rolling branch covers n <= L+8. Once rolling starts, the first step
    # is W+L+1 and W is at least L+6, so a trajectory needs n >= 2L+7.
    # Therefore:
    #   n <= L+8                  -> do not roll
    #   L+8 < n < 2L+7           -> do not roll (the former empty gap)
    #   n >= max(L+9, 2L+7)      -> rolling can produce a trajectory
    return max(lag_window + 9, 2 * lag_window + 7)


def _rolling_lifecycle_available(
    analysis_input: AnalysisInput,
    train_rows: Sequence[Mapping[str, float]],
) -> bool:
    return len(train_rows) >= _rolling_lifecycle_min_observations(
        analysis_input.lag_window
    )


def _report_warnings(
    analysis_input: AnalysisInput,
    train_rows: Sequence[Mapping[str, float]],
) -> list[dict[str, str]]:
    if _rolling_lifecycle_available(analysis_input, train_rows):
        return []
    observed = len(train_rows)
    required = _rolling_lifecycle_min_observations(analysis_input.lag_window)
    return [
        {
            "code": "stability_not_evaluated",
            "message": (
                "Temporal stability was not evaluated: this run has "
                f"{observed} observations; at least {required} are required "
                f"when lag_window={analysis_input.lag_window}."
            ),
        }
    ]


def _apply_gate_decisions(
    relation_views: list[dict[str, Any]],
    gate: EvidenceGateResult,
) -> list[dict[str, Any]]:
    decisions = {decision.relation.source: decision for decision in gate.decisions}
    output = []
    for view in relation_views:
        decision = decisions[view["source"]]
        view = dict(view)
        view["selected"] = decision.selected
        view["reason_code"] = decision.reason
        view["reason_text"] = _reason_text(decision.reason)
        view["significance"] = {
            "p_value": decision.p_value,
            "fdr_threshold": decision.fdr_threshold,
            "clears": decision.p_value <= decision.fdr_threshold,
        }
        view["sample_support"] = decision.sample_support
        view["effect"] = {
            **view["effect"],
            "effect_size_vs_noise_floor": decision.effect_size,
        }
        output.append(view)
    return output


def _baseline_block(analysis_input: AnalysisInput) -> dict[str, Any]:
    baseline_test_start = analysis_input.baseline_test_start or _first_baseline_label_date(
        analysis_input
    )
    label_rows = [
        index
        for index, date in enumerate(analysis_input.dates)
        if index >= analysis_input.lag_window and date >= baseline_test_start
    ]
    if not label_rows:
        return {"name": "persistence", "mae": None}
    actual = [float(analysis_input.rows[index][analysis_input.target]) for index in label_rows]
    predicted = predict_persistence(analysis_input.rows, label_rows, analysis_input.target)
    mae = sum(abs(left - right) for left, right in zip(actual, predicted)) / len(actual)
    return {"name": "persistence", "mae": mae}


def _first_baseline_label_date(analysis_input: AnalysisInput) -> str:
    train_dates = [
        date
        for index, date in enumerate(analysis_input.dates)
        if index >= analysis_input.lag_window and date <= analysis_input.train_end
    ]
    return train_dates[0] if train_dates else analysis_input.train_end


def _noise_floor_block(
    relations: Sequence[RelationWeight],
    lag_window: int,
    candidate_count: int,
) -> dict[str, Any]:
    sample_count = max(relation.sample_count for relation in relations)
    comparisons = max(1, lag_window * candidate_count)
    floor = correlation_noise_floor(sample_count, comparisons=comparisons)
    return {
        "sample_count": floor.sample_count,
        "comparisons": floor.comparisons,
        "alpha": floor.alpha,
        "threshold": floor.threshold,
    }


def _prediction_confidence_block(gate: EvidenceGateResult) -> dict[str, Any]:
    selected = gate.selected_relations
    if not selected:
        confidence = compute_prediction_confidence(
            relation_stability=None,
            parameter_uncertainty=None,
            input_support=None,
            residual_uncertainty=None,
        )
    else:
        confidence = compute_prediction_confidence(
            relation_stability=mean(
                relation.stability for relation in selected if relation.stability is not None
            ),
            parameter_uncertainty=mean(
                relation.uncertainty for relation in selected if relation.uncertainty is not None
            ),
            input_support=1.0,
            residual_uncertainty=None,
        )
    capped_by = (
        "input_support"
        if confidence.confidence is not None
        and confidence.input_support is not None
        and confidence.confidence == confidence.input_support
        and confidence.input_support < 1.0
        else None
    )
    return {
        "confidence": confidence.confidence,
        "components": {
            "relation_stability": confidence.relation_stability,
            "parameter_uncertainty": confidence.parameter_uncertainty,
            "input_support": confidence.input_support,
            "residual_uncertainty": confidence.residual_uncertainty,
        },
        "capped_by": capped_by,
    }


# Report narrative is hashed Report content. Change it in a standalone commit
# and record the pipeline_version before/after so version movement is attributable.
def _narrative(outcome: str, gate: EvidenceGateResult, relation_count: int) -> dict[str, Any]:
    if outcome == "ok":
        selected = len(gate.selected_relations)
        return {
            "headline": f"{selected} candidate relation{'s' if selected != 1 else ''} cleared the evidence gate for this run.",
            "lines": [
                f"{selected} of {relation_count} candidates cleared the evidence gate.",
                (
                    "Delta reports only relationships that survive stationarity, "
                    "stability, uncertainty, support, and FDR checks."
                ),
            ],
        }
    return {
        "headline": "No candidate relation cleared the evidence gate - baseline retained.",
        "lines": [
            f"0 of {relation_count} candidates cleared the evidence gate.",
            "Delta defers to persistence rather than fit a model it cannot defend.",
        ],
    }


def _reason_text(reason: str) -> str:
    return {
        "selected": "Clears effect, stability, support, uncertainty, and FDR.",
        "below_fdr_corrected_effect": "Does not survive the FDR-corrected effect threshold.",
        "insufficient_stability": "Evidence is not stable enough to select.",
        "excess_relationship_uncertainty": "Relationship uncertainty is too high.",
        "insufficient_sample_support": "Sample support is too low.",
        "not_selected": "Not selected by the evidence gate.",
    }.get(reason, reason)


def _parse_month(value: str, label: str) -> int:
    parts = value.split("-")
    if len(parts) != 2 or len(parts[0]) != 4 or len(parts[1]) != 2:
        raise validation_error("invalid_date", f"{label} must use YYYY-MM format.")
    try:
        year = int(parts[0])
        month = int(parts[1])
    except ValueError as exc:
        raise validation_error("invalid_date", f"{label} must use YYYY-MM format.") from exc
    if not 1 <= month <= 12:
        raise validation_error("invalid_date", f"{label} month must be between 01 and 12.")
    return year * 12 + month


def _month_label(month_index: int) -> str:
    year = (month_index - 1) // 12
    month = (month_index - 1) % 12 + 1
    return f"{year:04d}-{month:02d}"


def _sign(value: float) -> int:
    if value > 0.0:
        return 1
    if value < 0.0:
        return -1
    return 0
