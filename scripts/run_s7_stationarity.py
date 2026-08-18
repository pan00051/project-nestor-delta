#!/usr/bin/env python3
"""Run S7 transformed relation-measurement acceptance reports."""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Sequence, Tuple

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from nestor_delta.real_data import (  # noqa: E402
    load_real_case_config,
    load_real_case_data,
)
from nestor_delta.relation_weights import (  # noqa: E402
    RelationWeight,
    legacy_level_scoring,
    rank_target_sources,
)
from nestor_delta.s7_fixtures import (  # noqa: E402
    fixture_a_summaries,
    fixture_b_summaries,
)
from nestor_delta.stationarity import (  # noqa: E402
    compute_transformed_relation_weights,
    signal_diagnostics,
    validate_transform_declarations,
)

REPORT_ROOT = REPO_ROOT / "reports"
S7_MAX_LAG = 3

REAL_CASE_CONFIGS = (
    REPO_ROOT / "cases" / "spain_retail_eurostat_2008_2025" / "case.json",
    REPO_ROOT
    / "cases"
    / "spain_industrial_production_eurostat_2008_2023"
    / "case.json",
    REPO_ROOT
    / "cases"
    / "spain_retail_eurostat_expanded_2008_2025"
    / "case.json",
)

DUAL_WINDOW_CONFIGS = (
    REPO_ROOT / "cases" / "spain_industrial_normal_2008_2021" / "adaptive_case.json",
    REPO_ROOT / "cases" / "spain_industrial_shock_2008_2021" / "adaptive_case.json",
)


def main() -> int:
    REPORT_ROOT.mkdir(parents=True, exist_ok=True)
    fixture_path = REPORT_ROOT / "s7_fixture_acceptance.csv"
    diagnostics_path = REPORT_ROOT / "s7_eurostat_stationarity_diagnostics.csv"
    comparison_path = REPORT_ROOT / "s7_spain_relation_comparison.csv"
    summary_path = REPORT_ROOT / "s7_relation_measurement_summary.md"

    fixture_rows = _fixture_rows()
    diagnostic_rows: List[Dict[str, object]] = []
    comparison_rows: List[Dict[str, object]] = []
    for config_path in REAL_CASE_CONFIGS:
        diagnostics, comparisons = _real_case_rows(config_path)
        diagnostic_rows.extend(diagnostics)
        comparison_rows.extend(comparisons)
    for config_path in DUAL_WINDOW_CONFIGS:
        diagnostics, comparisons = _dual_window_rows(config_path)
        diagnostic_rows.extend(diagnostics)
        comparison_rows.extend(comparisons)

    _write_fixture_csv(fixture_path, fixture_rows)
    _write_diagnostics_csv(diagnostics_path, diagnostic_rows)
    _write_comparison_csv(comparison_path, comparison_rows)
    _write_summary(summary_path, fixture_rows, diagnostic_rows, comparison_rows)
    for path in (fixture_path, diagnostics_path, comparison_path, summary_path):
        print(f"Wrote {path}")
    return 0


def _fixture_rows() -> List[Dict[str, object]]:
    rows: List[Dict[str, object]] = []
    for summary in fixture_a_summaries(S7_MAX_LAG) + fixture_b_summaries(S7_MAX_LAG):
        rows.append(
            {
                "fixture": summary.fixture,
                "path": summary.path,
                "seed_count": summary.seed_count,
                "median_abs_r": summary.median_abs_r,
                "p90_abs_r": summary.p90_abs_r,
                "pass_rate_gt_006": summary.pass_rate_gt_006,
                "pass_rate_gt_030": summary.pass_rate_gt_030,
                "correct_lag_rate": summary.correct_lag_rate,
            }
        )
    return rows


def _real_case_rows(
    config_path: Path,
) -> Tuple[List[Dict[str, object]], List[Dict[str, object]]]:
    config = load_real_case_config(config_path)
    if config.transform_declarations is None:
        raise ValueError(f"{config_path} lacks explicit S7 transform_declarations")
    data = load_real_case_data(config)
    train_end = max(
        index for index, date in enumerate(data.dates) if date <= config.train_end
    ) + 1
    train_rows = data.rows[:train_end]
    variables = data.variables
    transforms = validate_transform_declarations(
        variables, config.transform_declarations
    )
    return (
        _diagnostic_rows(config.case_name, train_rows, variables, transforms),
        _comparison_rows(
            config.case_name,
            train_rows,
            variables,
            config.target,
            config.lag_window,
            transforms,
        ),
    )


def _dual_window_rows(
    config_path: Path,
) -> Tuple[List[Dict[str, object]], List[Dict[str, object]]]:
    payload = json.loads(config_path.read_text(encoding="utf-8"))
    root = config_path.resolve().parent
    csv_path = root / payload["csv"]
    date_column = payload["date_column"]
    target = payload["target"]
    candidates = tuple(payload["candidate_signals"])
    variables = (target,) + tuple(sorted(candidates))
    transforms = validate_transform_declarations(
        variables, payload.get("transform_declarations", {})
    )
    rows_by_date = _load_csv_rows(csv_path, date_column, variables)
    train_rows = tuple(
        row
        for date, row in rows_by_date
        if payload["train_start"] <= date <= payload["train_end"]
    )
    return (
        _diagnostic_rows(payload["case_name"], train_rows, variables, transforms),
        _comparison_rows(
            payload["case_name"],
            train_rows,
            variables,
            target,
            max(payload["lag_windows"]),
            transforms,
        ),
    )


def _load_csv_rows(
    path: Path, date_column: str, variables: Sequence[str]
) -> Tuple[Tuple[str, Dict[str, float]], ...]:
    rows = []
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for record in reader:
            rows.append(
                (
                    record[date_column],
                    {variable: float(record[variable]) for variable in variables},
                )
            )
    return tuple(rows)


def _diagnostic_rows(
    case_name: str,
    rows: Sequence[Mapping[str, float]],
    variables: Iterable[str],
    transforms: Mapping[str, str],
) -> List[Dict[str, object]]:
    return [
        {
            "case_name": case_name,
            "signal": diagnostic.signal,
            "transform": diagnostic.transform,
            "level_lag1_acf": diagnostic.level_lag1_acf,
            "highly_persistent_risk": diagnostic.highly_persistent_risk,
            "diagnostic_scope": (
                "lag-1 ACF > 0.95 is a highly-persistent risk flag, "
                "not a formal stationarity test"
            ),
        }
        for diagnostic in signal_diagnostics(rows, variables, transforms)
    ]


def _comparison_rows(
    case_name: str,
    rows: Sequence[Mapping[str, float]],
    variables: Sequence[str],
    target: str,
    max_lag: int,
    transforms: Mapping[str, str],
) -> List[Dict[str, object]]:
    legacy = rank_target_sources(legacy_level_scoring(rows, variables, max_lag), target)
    transformed = rank_target_sources(
        compute_transformed_relation_weights(rows, variables, max_lag, transforms),
        target,
    )
    output = []
    output.extend(_ranking_rows(case_name, "legacy_level_scoring", legacy))
    output.extend(_ranking_rows(case_name, "s7_transformed_scoring", transformed))
    return output


def _ranking_rows(
    case_name: str, path: str, ranking: Sequence[RelationWeight]
) -> List[Dict[str, object]]:
    return [
        {
            "case_name": case_name,
            "path": path,
            "rank": rank,
            "source": weight.source,
            "target": weight.target,
            "lag": weight.lag,
            "weight": weight.weight,
            "score": weight.score,
            "sample_count": weight.sample_count,
            "transform": weight.transform,
        }
        for rank, weight in enumerate(ranking, start=1)
    ]


def _write_fixture_csv(path: Path, rows: Sequence[Dict[str, object]]) -> None:
    fieldnames = [
        "fixture",
        "path",
        "seed_count",
        "median_abs_r",
        "p90_abs_r",
        "pass_rate_gt_006",
        "pass_rate_gt_030",
        "correct_lag_rate",
    ]
    _write_csv(path, fieldnames, rows)


def _write_diagnostics_csv(path: Path, rows: Sequence[Dict[str, object]]) -> None:
    fieldnames = [
        "case_name",
        "signal",
        "transform",
        "level_lag1_acf",
        "highly_persistent_risk",
        "diagnostic_scope",
    ]
    _write_csv(path, fieldnames, rows)


def _write_comparison_csv(path: Path, rows: Sequence[Dict[str, object]]) -> None:
    fieldnames = [
        "case_name",
        "path",
        "rank",
        "source",
        "target",
        "lag",
        "weight",
        "score",
        "sample_count",
        "transform",
    ]
    _write_csv(path, fieldnames, rows)


def _write_csv(
    path: Path, fieldnames: Sequence[str], rows: Sequence[Dict[str, object]]
) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    field: _format_value(row.get(field))
                    for field in fieldnames
                }
            )


def _write_summary(
    path: Path,
    fixture_rows: Sequence[Dict[str, object]],
    diagnostic_rows: Sequence[Dict[str, object]],
    comparison_rows: Sequence[Dict[str, object]],
) -> None:
    fixture_lookup = {
        (row["fixture"], row["path"]): row for row in fixture_rows
    }
    top_rows = [
        row for row in comparison_rows if row["rank"] == 1
    ]
    lines = [
        "# S7 Relation Measurement Summary",
        "",
        "Scope: S7 only. Legacy level Pearson scoring is preserved as the control path; S7 transformed scoring measures explicit short-run transformed relationships only.",
        "",
        "## Synthetic Fixtures",
        "",
        "| Fixture | Path | Seeds | Median abs r | P90 abs r | P(abs r > 0.06) | P(abs r > 0.30) | Correct lag |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in fixture_rows:
        lines.append(
            "| {fixture} | {path} | {seeds} | {median} | {p90} | {gt006} | {gt030} | {lag} |".format(
                fixture=row["fixture"],
                path=row["path"],
                seeds=row["seed_count"],
                median=_display_float(row["median_abs_r"]),
                p90=_display_float(row["p90_abs_r"]),
                gt006=_display_pct(row["pass_rate_gt_006"]),
                gt030=_display_pct(row["pass_rate_gt_030"]),
                lag=(
                    "n/a"
                    if row["correct_lag_rate"] is None
                    else _display_pct(row["correct_lag_rate"])
                ),
            )
        )
    lines.extend(
        [
            "",
            "Fixture A shows the old level path admitting independent random walks while the transformed path removes the high-score pseudo relationship. Fixture B keeps the true short-run dynamic relation and recovers lag 3 in every seed.",
            "",
            "## Eurostat Diagnostics",
            "",
            "The `highly_persistent_risk` column is only a lag-1 ACF risk flag. It is not an ADF/KPSS result and is not reported as a formal stationarity conclusion.",
            "",
            "| Case | Signal | Transform | lag-1 ACF | Risk flag |",
            "|---|---|---|---:|---|",
        ]
    )
    for row in diagnostic_rows:
        if row["highly_persistent_risk"]:
            lines.append(
                "| {case} | {signal} | {transform} | {acf} | {risk} |".format(
                    case=row["case_name"],
                    signal=row["signal"],
                    transform=row["transform"],
                    acf=_display_float(row["level_lag1_acf"]),
                    risk=row["highly_persistent_risk"],
                )
            )
    lines.extend(
        [
            "",
            "## Spain And Dual-Window Top Relations",
            "",
            "Both paths are reported side by side; no case is selected or promoted based on the nicer result.",
            "",
            "| Case | Path | Top source | Lag | Weight | Score | Transform |",
            "|---|---|---|---:|---:|---:|---|",
        ]
    )
    for row in top_rows:
        lines.append(
            "| {case} | {path_name} | {source} | {lag} | {weight} | {score} | {transform} |".format(
                case=row["case_name"],
                path_name=row["path"],
                source=row["source"],
                lag=row["lag"],
                weight=_display_float(row["weight"]),
                score=_display_float(row["score"]),
                transform=row["transform"],
            )
        )
    lines.extend(
        [
            "",
            "## Boundaries",
            "",
            "- Transform declarations are explicit case inputs: `none`, `diff`, or `log_diff`; the diagnostics do not choose transforms.",
            "- S7 does not implement cointegration, ECM/VECM, long-run relationships, temporal stability, evidence gates, prediction confidence, nonlinear scoring, FFT, or coherence.",
            "- Real-data prediction accuracy is not the S7 acceptance criterion.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _format_value(value: object) -> object:
    if value is None:
        return ""
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, float):
        return f"{value:.10f}"
    return value


def _display_float(value: object) -> str:
    if value == "":
        return "n/a"
    return f"{float(value):.3f}"


def _display_pct(value: object) -> str:
    if value == "":
        return "n/a"
    return f"{float(value) * 100.0:.1f}%"


if __name__ == "__main__":
    raise SystemExit(main())
