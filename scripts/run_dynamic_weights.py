#!/usr/bin/env python3
"""Generate Sprint 4 drift data and compare static with dynamic weights."""

from __future__ import annotations

import csv
import sys
from pathlib import Path
from statistics import mean

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from nestor_delta.config import TEST_LABEL_ROWS  # noqa: E402
from nestor_delta.dynamic_prediction import (  # noqa: E402
    fit_dynamic_drift_predictor,
    fit_static_drift_predictor,
    predict_dynamic_drift,
    predict_static_drift,
)
from nestor_delta.dynamic_weights import target_source_trajectory  # noqa: E402
from nestor_delta.metrics import mae, rmse  # noqa: E402
from nestor_delta.reporting import summarize_metrics  # noqa: E402
from nestor_delta.s4_config import (  # noqa: E402
    DRIFT_SEEDS,
    DYNAMIC_TRAIN_LABEL_ROWS,
    DYNAMIC_WINDOW,
)
from nestor_delta.synthetic_drift import (  # noqa: E402
    driver_a_coefficient,
    generate_drift_series,
    generate_drift_truth,
    write_drift_series_csv,
    write_drift_truth_csv,
)


def main() -> int:
    data_dir = REPO_ROOT / "data" / "synthetic_drift"
    reports_dir = REPO_ROOT / "reports"
    metric_rows = []
    trajectory_rows = []
    tracking_rows = []

    for seed in DRIFT_SEEDS:
        rows = generate_drift_series(seed)
        write_drift_series_csv(
            rows, data_dir / f"synthetic_drift_seed_{seed}.csv"
        )
        write_drift_truth_csv(
            generate_drift_truth(),
            data_dir / f"synthetic_drift_truth_seed_{seed}.csv",
        )

        labels = [float(rows[index]["target"]) for index in TEST_LABEL_ROWS]
        static_model = fit_static_drift_predictor(
            rows, DYNAMIC_TRAIN_LABEL_ROWS
        )
        dynamic_model = fit_dynamic_drift_predictor(
            rows, DYNAMIC_TRAIN_LABEL_ROWS
        )
        static_predictions = predict_static_drift(
            rows, TEST_LABEL_ROWS, static_model
        )
        dynamic_predictions, timed_weights = predict_dynamic_drift(
            rows, TEST_LABEL_ROWS, dynamic_model
        )
        metric_rows.append(
            _metric_row("static_weights", seed, labels, static_predictions)
        )
        metric_rows.append(
            _metric_row("dynamic_weights", seed, labels, dynamic_predictions)
        )

        static_weight = next(
            weight
            for weight in static_model.selected_weights
            if weight.source == "driver_a" and weight.target == "target"
        )
        dynamic_trajectory = target_source_trajectory(
            timed_weights, "target", "driver_a"
        )
        for weight in dynamic_trajectory:
            trajectory_rows.append(
                {
                    "seed": seed,
                    "step": weight.step,
                    "truth_coefficient": driver_a_coefficient(weight.step),
                    "static_weight": static_weight.weight,
                    "dynamic_weight": weight.weight,
                    "dynamic_lag": weight.lag,
                    "window_start": weight.window_start,
                    "window_end_exclusive": weight.window_end,
                    "sample_count": weight.sample_count,
                }
            )

        first = dynamic_trajectory[0]
        last = dynamic_trajectory[-1]
        tracking_rows.append(
            {
                "seed": seed,
                "truth_start": driver_a_coefficient(first.step),
                "truth_end": driver_a_coefficient(last.step),
                "static_weight": static_weight.weight,
                "dynamic_start": first.weight,
                "dynamic_end": last.weight,
                "dynamic_change": last.weight - first.weight,
                "correct_direction": last.weight > first.weight,
            }
        )

    summaries = summarize_metrics(metric_rows)
    _write_metrics(metric_rows, reports_dir / "dynamic_weight_metrics.csv")
    _write_trajectory(
        trajectory_rows, reports_dir / "dynamic_weight_trajectory.csv"
    )
    _write_tracking(
        tracking_rows, reports_dir / "dynamic_weight_tracking.csv"
    )
    _write_summary(
        summaries, tracking_rows, reports_dir / "dynamic_weight_summary.md"
    )

    print("Wrote data/synthetic_drift/synthetic_drift*_seed_<seed>.csv")
    print("Wrote reports/dynamic_weight_metrics.csv")
    print("Wrote reports/dynamic_weight_trajectory.csv")
    print("Wrote reports/dynamic_weight_tracking.csv")
    print("Wrote reports/dynamic_weight_summary.md")
    for row in summaries:
        print(
            "{baseline}: MAE mean={mae_mean:.6f} range={mae_min:.6f}-{mae_max:.6f}; "
            "RMSE mean={rmse_mean:.6f} range={rmse_min:.6f}-{rmse_max:.6f}".format(
                **row
            )
        )
    return 0


def _metric_row(method, seed, labels, predictions):
    return {
        "baseline": method,
        "seed": float(seed),
        "split": "test_prequential",
        "mae": mae(labels, predictions),
        "rmse": rmse(labels, predictions),
        "sample_count": float(len(labels)),
    }


def _write_metrics(rows, path: Path) -> None:
    fieldnames = ["baseline", "seed", "split", "mae", "rmse", "sample_count"]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    **row,
                    "seed": int(row["seed"]),
                    "mae": f"{row['mae']:.10f}",
                    "rmse": f"{row['rmse']:.10f}",
                    "sample_count": int(row["sample_count"]),
                }
            )


def _write_trajectory(rows, path: Path) -> None:
    fieldnames = [
        "seed",
        "step",
        "truth_coefficient",
        "static_weight",
        "dynamic_weight",
        "dynamic_lag",
        "window_start",
        "window_end_exclusive",
        "sample_count",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    **row,
                    "truth_coefficient": f"{row['truth_coefficient']:.10f}",
                    "static_weight": f"{row['static_weight']:.10f}",
                    "dynamic_weight": f"{row['dynamic_weight']:.10f}",
                }
            )


def _write_tracking(rows, path: Path) -> None:
    fieldnames = [
        "seed",
        "truth_start",
        "truth_end",
        "static_weight",
        "dynamic_start",
        "dynamic_end",
        "dynamic_change",
        "correct_direction",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    **row,
                    "truth_start": f"{row['truth_start']:.10f}",
                    "truth_end": f"{row['truth_end']:.10f}",
                    "static_weight": f"{row['static_weight']:.10f}",
                    "dynamic_start": f"{row['dynamic_start']:.10f}",
                    "dynamic_end": f"{row['dynamic_end']:.10f}",
                    "dynamic_change": f"{row['dynamic_change']:.10f}",
                    "correct_direction": str(row["correct_direction"]).lower(),
                }
            )


def _write_summary(metrics, tracking, path: Path) -> None:
    by_method = {row["baseline"]: row for row in metrics}
    static = by_method["static_weights"]
    dynamic = by_method["dynamic_weights"]
    mae_reduction = _relative_reduction(dynamic["mae_mean"], static["mae_mean"])
    rmse_reduction = _relative_reduction(
        dynamic["rmse_mean"], static["rmse_mean"]
    )
    direction_count = sum(row["correct_direction"] for row in tracking)

    lines = [
        "# Sprint 4 Dynamic Weight Summary",
        "",
        "Protocol: additive frozen S4 drift protocol in `EVALUATION.md`; five independent seeds and a 120-row causal rolling window.",
        "",
        "The frozen OLS coefficients and source selection use train labels only. At test step `t`, dynamic relation weights use rows `t-120` through `t-1`; after prediction, row `t` becomes available only to later steps.",
        "",
        "## Known-Drift Tracking",
        "",
        "`truth` is the generative lag-1 coefficient. `static weight` and `dynamic weight` are marginal Pearson relation weights, so direction and movement are compared rather than coefficient equality.",
        "",
        "| Seed | Truth start | Truth end | Static weight | Dynamic start | Dynamic end | Dynamic change | Correct direction |",
        "|---:|---:|---:|---:|---:|---:|---:|:---:|",
    ]
    for row in tracking:
        lines.append(
            "| {seed} | {truth_start:.6f} | {truth_end:.6f} | {static_weight:.6f} | "
            "{dynamic_start:.6f} | {dynamic_end:.6f} | {dynamic_change:+.6f} | {direction} |".format(
                **row,
                direction="yes" if row["correct_direction"] else "no",
            )
        )
    lines.extend(
        [
            "",
            f"Tracking acceptance: {direction_count}/{len(tracking)} seeds move in the known positive drift direction from test start to test end.",
            "The complete test-step truth/static/dynamic trajectory is in `reports/dynamic_weight_trajectory.csv`.",
            "",
            "## Prediction Comparison",
            "",
            "| Mode | Runs | MAE mean | MAE range | RMSE mean | RMSE range |",
            "|---|---:|---:|---:|---:|---:|",
        ]
    )
    for row in metrics:
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
            f"Dynamic weights reduce mean MAE by {mae_reduction:.2f}% and mean RMSE by {rmse_reduction:.2f}% versus static weights on the frozen drift test.",
            "",
            "## Boundary",
            "",
            "This is deterministic rolling adaptation of Sprint 2 relation weights. It does not tune the window, refit OLS after training, implement ignore-value resource adaptation, or modify S0-S3.1 logic and data.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _relative_reduction(new_value: float, baseline_value: float) -> float:
    return (baseline_value - new_value) / baseline_value * 100.0


if __name__ == "__main__":
    raise SystemExit(main())
