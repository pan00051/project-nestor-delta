#!/usr/bin/env python3
"""Run a Sprint 6 author-prepared real-data case."""

from __future__ import annotations

import csv
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from nestor_delta.real_case_analysis import run_real_case_analysis  # noqa: E402
from nestor_delta.real_data import (  # noqa: E402
    load_real_case_config,
    load_real_case_data,
)


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("Usage: python scripts/run_real_case.py cases/<case_name>/case.json")
        return 2

    config = load_real_case_config(Path(argv[1]))
    data = load_real_case_data(config)
    result = run_real_case_analysis(config, data)
    config.output_dir.mkdir(parents=True, exist_ok=True)

    _write_relation_ranking(config.output_dir / "relation_ranking.csv", result)
    _write_prediction_metrics(config.output_dir / "prediction_metrics.csv", result)
    _write_predictions(config.output_dir / "predictions_vs_actual.csv", result)
    _write_resource_tradeoff(config.output_dir / "resource_tradeoff.csv", result)
    _write_summary(config.output_dir / "summary.md", config, data, result)

    print(f"Wrote {config.output_dir / 'relation_ranking.csv'}")
    print(f"Wrote {config.output_dir / 'prediction_metrics.csv'}")
    print(f"Wrote {config.output_dir / 'predictions_vs_actual.csv'}")
    print(f"Wrote {config.output_dir / 'resource_tradeoff.csv'}")
    print(f"Wrote {config.output_dir / 'summary.md'}")
    return 0


def _write_relation_ranking(path: Path, result) -> None:
    fieldnames = [
        "rank",
        "source",
        "selected",
        "lag",
        "weight",
        "score",
        "sample_count",
    ]
    selected_sources = {weight.source for weight in result.selected_weights}
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for rank, weight in enumerate(result.ranking, start=1):
            writer.writerow(
                {
                    "rank": rank,
                    "source": weight.source,
                    "selected": str(weight.source in selected_sources).lower(),
                    "lag": weight.lag,
                    "weight": f"{weight.weight:.10f}",
                    "score": f"{weight.score:.10f}",
                    "sample_count": weight.sample_count,
                }
            )


def _write_prediction_metrics(path: Path, result) -> None:
    fieldnames = ["method", "mae", "rmse", "sample_count"]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for row in sorted(result.metric_rows, key=lambda item: str(item["method"])):
            writer.writerow(
                {
                    "method": row["method"],
                    "mae": f"{float(row['mae']):.10f}",
                    "rmse": f"{float(row['rmse']):.10f}",
                    "sample_count": int(row["sample_count"]),
                }
            )


def _write_predictions(path: Path, result) -> None:
    fieldnames = list(result.prediction_rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for row in result.prediction_rows:
            writer.writerow(
                {
                    key: (f"{value:.10f}" if isinstance(value, float) else value)
                    for key, value in row.items()
                }
            )


def _write_resource_tradeoff(path: Path, result) -> None:
    fieldnames = [
        "budget_ratio",
        "threshold",
        "retained_relation_count",
        "downstream_compute_proxy",
        "downstream_memory_proxy",
        "retained_sources",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for row in result.resource_rows:
            writer.writerow(
                {
                    **row,
                    "budget_ratio": f"{float(row['budget_ratio']):.2f}",
                    "threshold": f"{float(row['threshold']):.10f}",
                }
            )


def _write_summary(path: Path, config, data, result) -> None:
    selected = ", ".join(weight.source for weight in result.selected_weights) or "none"
    best_metric = min(result.metric_rows, key=lambda row: float(row["mae"]))
    lines = [
        f"# Real Data Case: {config.case_name}",
        "",
        "Scope: exploratory real-data case runner. This report is limited to co-movement and out-of-sample predictive usefulness.",
        "",
        f"- CSV: `{config.csv_path}`",
        f"- Target: `{config.target}`",
        f"- Candidate signals: {len(config.candidate_signals)}",
        f"- Rows: {len(data.rows)}",
        f"- Train labels: {len(result.train_label_rows)}",
        f"- Test labels: {len(result.test_label_rows)}",
        f"- Lag window: {config.lag_window}",
        f"- Auto-selected signals: {selected}",
        f"- Fit status: `{result.fit_status}`",
        f"- Best MAE method in this run: `{best_metric['method']}`",
        "",
        "## Prediction Metrics",
        "",
        "| Method | MAE | RMSE | Test samples |",
        "|---|---:|---:|---:|",
    ]
    for row in sorted(result.metric_rows, key=lambda item: str(item["method"])):
        lines.append(
            "| {method} | {mae:.6f} | {rmse:.6f} | {sample_count} |".format(
                method=row["method"],
                mae=float(row["mae"]),
                rmse=float(row["rmse"]),
                sample_count=int(row["sample_count"]),
            )
        )
    if result.fit_status == "baseline_only_no_stable_signal":
        lines.extend(
            [
                "",
                "No signal satisfied numerical stability requirements in the selected set, so the report keeps baseline metrics only.",
            ]
        )
    if result.dropped_collinear_sources:
        dropped = ", ".join(result.dropped_collinear_sources)
        lines.extend(
            [
                "",
                "Collinearity backoff removed lower-ranked overlapping signals: "
                f"{dropped}. This means they did not add stable extra linear information "
                "beyond higher-ranked retained signals in this fit; it does not label them as useless.",
            ]
        )
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "- Candidate pool is author-defined, but ranking and selection are automatic.",
            "- Ranking, selection, and fitted coefficients use train rows only.",
            "- Test rows are used only for out-of-sample evaluation.",
            "- CSV column order must not be interpreted as signal priority.",
        ]
    )
    if config.notes:
        lines.extend(["", "## Notes", "", config.notes])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
