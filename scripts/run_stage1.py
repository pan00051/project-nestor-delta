#!/usr/bin/env python3
"""Run Sprint 3 weighted three-variable prediction."""

from __future__ import annotations

import csv
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from nestor_delta.baselines import (  # noqa: E402
    fit_linear_regression,
    predict_linear_regression,
    predict_persistence,
)
from nestor_delta.config import SEEDS, TEST_LABEL_ROWS, TRAIN_LABEL_ROWS  # noqa: E402
from nestor_delta.metrics import mae, rmse  # noqa: E402
from nestor_delta.reporting import summarize_metrics, write_metrics_csv  # noqa: E402
from nestor_delta.splits import build_lagged_samples  # noqa: E402
from nestor_delta.stage1_prediction import (  # noqa: E402
    fit_stage1_weighted_predictor,
    predict_stage1_weighted,
)
from nestor_delta.synthetic import generate_series  # noqa: E402


def main() -> int:
    reports_dir = REPO_ROOT / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    metric_rows = []
    selection_rows = []

    for seed in SEEDS:
        rows = generate_series(seed)
        train_features, train_labels = build_lagged_samples(rows, TRAIN_LABEL_ROWS)
        test_features, test_labels = build_lagged_samples(rows, TEST_LABEL_ROWS)

        persistence_predictions = predict_persistence(rows, TEST_LABEL_ROWS)
        metric_rows.append(_metric_row("persistence", seed, test_labels, persistence_predictions))

        linear_coefficients = fit_linear_regression(train_features, train_labels)
        linear_predictions = predict_linear_regression(test_features, linear_coefficients)
        metric_rows.append(_metric_row("linear_regression", seed, test_labels, linear_predictions))

        stage1_model = fit_stage1_weighted_predictor(rows, TRAIN_LABEL_ROWS)
        stage1_predictions = predict_stage1_weighted(rows, TEST_LABEL_ROWS, stage1_model)
        metric_rows.append(_metric_row("stage1_weighted_three_variable", seed, test_labels, stage1_predictions))

        for rank, weight in enumerate(stage1_model.selected_weights, start=1):
            selection_rows.append(
                {
                    "seed": seed,
                    "rank": rank,
                    "source": weight.source,
                    "selected_lag": weight.lag,
                    "weight": weight.weight,
                    "score": weight.score,
                    "sample_count": weight.sample_count,
                }
            )

    summaries = summarize_metrics(metric_rows)
    write_metrics_csv(metric_rows, reports_dir / "stage1_metrics.csv")
    _write_selection_csv(selection_rows, reports_dir / "stage1_selected_sources.csv")
    _write_stage1_summary(summaries, reports_dir / "stage1_summary.md")

    print("Wrote reports/stage1_metrics.csv")
    print("Wrote reports/stage1_selected_sources.csv")
    print("Wrote reports/stage1_summary.md")
    for row in summaries:
        print(
            "{baseline}: MAE mean={mae_mean:.6f} range={mae_min:.6f}-{mae_max:.6f}; "
            "RMSE mean={rmse_mean:.6f} range={rmse_min:.6f}-{rmse_max:.6f}".format(**row)
        )
    return 0


def _metric_row(baseline, seed, labels, predictions):
    return {
        "baseline": baseline,
        "seed": float(seed),
        "split": "test",
        "mae": mae(labels, predictions),
        "rmse": rmse(labels, predictions),
        "sample_count": float(len(labels)),
    }


def _write_selection_csv(rows, path: Path) -> None:
    fieldnames = ["seed", "rank", "source", "selected_lag", "weight", "score", "sample_count"]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "seed": row["seed"],
                    "rank": row["rank"],
                    "source": row["source"],
                    "selected_lag": row["selected_lag"],
                    "weight": f"{row['weight']:.10f}",
                    "score": f"{row['score']:.10f}",
                    "sample_count": row["sample_count"],
                }
            )


def _write_stage1_summary(summaries, path: Path) -> None:
    by_name = {row["baseline"]: row for row in summaries}
    stage1 = by_name["stage1_weighted_three_variable"]
    persistence = by_name["persistence"]
    linear = by_name["linear_regression"]
    mae_vs_persistence = _relative_reduction(stage1["mae_mean"], persistence["mae_mean"])
    rmse_vs_persistence = _relative_reduction(stage1["rmse_mean"], persistence["rmse_mean"])
    mae_vs_linear = _relative_reduction(stage1["mae_mean"], linear["mae_mean"])
    rmse_vs_linear = _relative_reduction(stage1["rmse_mean"], linear["rmse_mean"])

    lines = [
        "# Sprint 3 Stage 1 Prediction Summary",
        "",
        "Protocol: `EVALUATION.md` v1 frozen split and metrics.",
        "",
        "Stage 1 combines Sprint 2 relation weights with Sprint 1 OLS prediction.",
        "For each seed, relation weights are computed on train rows only; the top two sources for `target` are selected; the predictor uses lagged `target` plus the two selected source variables.",
        "",
        "| Method | Runs | MAE mean | MAE range | RMSE mean | RMSE range |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for row in summaries:
        lines.append(
            "| {baseline} | {runs} | {mae_mean:.6f} | {mae_min:.6f}-{mae_max:.6f} | "
            "{rmse_mean:.6f} | {rmse_min:.6f}-{rmse_max:.6f} |".format(
                baseline=row["baseline"],
                runs=int(row["runs"]),
                mae_mean=row["mae_mean"],
                mae_min=row["mae_min"],
                mae_max=row["mae_max"],
                rmse_mean=row["rmse_mean"],
                rmse_min=row["rmse_min"],
                rmse_max=row["rmse_max"],
            )
        )
    lines.extend(
        [
            "",
            "## Improvement",
            "",
            f"- MAE vs persistence: {mae_vs_persistence:.2f}% lower.",
            f"- RMSE vs persistence: {rmse_vs_persistence:.2f}% lower.",
            f"- MAE vs Sprint 1 linear regression: {mae_vs_linear:.2f}% lower.",
            f"- RMSE vs Sprint 1 linear regression: {rmse_vs_linear:.2f}% lower.",
            "",
            "## Boundary",
            "",
            "This is a fixed Stage 1 workflow. It does not implement dynamic weights, ignore values, resource adaptation, or event attribution.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _relative_reduction(new_value: float, baseline_value: float) -> float:
    return (baseline_value - new_value) / baseline_value * 100.0


if __name__ == "__main__":
    raise SystemExit(main())
