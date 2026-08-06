#!/usr/bin/env python3
"""Run Sprint 5 resource-adaptive ignore validation."""

from __future__ import annotations

import csv
import sys
from pathlib import Path
from statistics import mean

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from nestor_delta.config import FEATURE_COLUMNS, LAG_WINDOW, TEST_LABEL_ROWS  # noqa: E402
from nestor_delta.metrics import mae, rmse  # noqa: E402
from nestor_delta.resource_adaptive_prediction import (  # noqa: E402
    fit_adaptive_ignore_predictor,
    predict_adaptive_ignore,
)
from nestor_delta.s4_config import DRIFT_SEEDS, DYNAMIC_TRAIN_LABEL_ROWS  # noqa: E402
from nestor_delta.s5_config import (  # noqa: E402
    BUDGET_RATIOS,
    RESOURCE_STRESS_COLUMNS,
    RESOURCE_STRESS_LAG_WINDOW,
    RESOURCE_STRESS_SEEDS,
    RESOURCE_STRESS_TEST_LABEL_ROWS,
    RESOURCE_STRESS_TRAIN_LABEL_ROWS,
)
from nestor_delta.synthetic_drift import generate_drift_series  # noqa: E402
from nestor_delta.synthetic_resource_stress import (  # noqa: E402
    generate_resource_stress_series,
    source_tier,
    write_resource_stress_csv,
)


def main() -> int:
    data_dir = REPO_ROOT / "data" / "synthetic_resource_stress"
    reports_dir = REPO_ROOT / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    metric_rows = []
    retention_rows = []

    for seed in DRIFT_SEEDS:
        rows = generate_drift_series(seed)
        _extend_track(
            metric_rows,
            retention_rows,
            track="s4_correctness_regression",
            seed=seed,
            rows=rows,
            variables=FEATURE_COLUMNS,
            train_label_rows=DYNAMIC_TRAIN_LABEL_ROWS,
            test_label_rows=TEST_LABEL_ROWS,
            lag_window=LAG_WINDOW,
        )

    for seed in RESOURCE_STRESS_SEEDS:
        rows = generate_resource_stress_series(seed)
        write_resource_stress_csv(
            rows, data_dir / f"resource_stress_seed_{seed}.csv"
        )
        _extend_track(
            metric_rows,
            retention_rows,
            track="resource_stress",
            seed=seed,
            rows=rows,
            variables=RESOURCE_STRESS_COLUMNS,
            train_label_rows=RESOURCE_STRESS_TRAIN_LABEL_ROWS,
            test_label_rows=RESOURCE_STRESS_TEST_LABEL_ROWS,
            lag_window=RESOURCE_STRESS_LAG_WINDOW,
        )

    _write_metrics(metric_rows, reports_dir / "resource_adaptive_metrics.csv")
    _write_retention(retention_rows, reports_dir / "resource_adaptive_retention.csv")
    _write_summary(
        _summarize_by_track_budget(metric_rows),
        reports_dir / "resource_adaptive_summary.md",
    )

    print("Wrote data/synthetic_resource_stress/resource_stress_seed_<seed>.csv")
    print("Wrote reports/resource_adaptive_metrics.csv")
    print("Wrote reports/resource_adaptive_retention.csv")
    print("Wrote reports/resource_adaptive_summary.md")
    for row in _summarize_by_track_budget(metric_rows):
        print(
            "{track} budget={budget_ratio:.2f} threshold={threshold:.2f}: "
            "retained mean={retained_relation_count_mean:.2f}; "
            "downstream_compute reduction={downstream_compute_reduction_pct_mean:.2f}%; "
            "MAE mean={mae_mean:.6f} loss={mae_loss_pct_mean:.2f}%".format(
                **row
            )
        )
    return 0


def _extend_track(
    metric_rows,
    retention_rows,
    track,
    seed,
    rows,
    variables,
    train_label_rows,
    test_label_rows,
    lag_window,
):
    labels = [float(rows[index]["target"]) for index in test_label_rows]
    models = [
        fit_adaptive_ignore_predictor(
            rows,
            train_label_rows,
            variables=variables,
            budget_ratio=budget_ratio,
            lag_window=lag_window,
        )
        for budget_ratio in BUDGET_RATIOS
    ]
    full_model = models[0]
    full_compute = full_model.profile.downstream_compute_proxy
    full_memory = full_model.profile.downstream_memory_proxy
    full_predictions = predict_adaptive_ignore(
        rows, test_label_rows, full_model, lag_window=lag_window
    )
    full_mae = mae(labels, full_predictions)
    full_rmse = rmse(labels, full_predictions)

    for model in models:
        predictions = predict_adaptive_ignore(
            rows, test_label_rows, model, lag_window=lag_window
        )
        current_mae = mae(labels, predictions)
        current_rmse = rmse(labels, predictions)
        profile = model.profile
        tier_counts = _tier_counts(model.retained_relations, track)
        metric_rows.append(
            {
                "track": track,
                "seed": seed,
                "budget_ratio": model.budget_ratio,
                "threshold": model.threshold,
                "retained_relation_count": profile.retained_relation_count,
                "retained_feature_count": profile.retained_feature_count,
                "downstream_compute_proxy": profile.downstream_compute_proxy,
                "downstream_memory_proxy": profile.downstream_memory_proxy,
                "estimated_memory_bytes": profile.estimated_memory_bytes,
                "downstream_compute_reduction_pct": _reduction(
                    profile.downstream_compute_proxy, full_compute
                ),
                "downstream_memory_reduction_pct": _reduction(
                    profile.downstream_memory_proxy, full_memory
                ),
                "mae": current_mae,
                "rmse": current_rmse,
                "mae_loss_pct": _increase(current_mae, full_mae),
                "rmse_loss_pct": _increase(current_rmse, full_rmse),
                **tier_counts,
            }
        )
        for rank, relation in enumerate(model.retained_relations, start=1):
            retention_rows.append(
                {
                    "track": track,
                    "seed": seed,
                    "budget_ratio": model.budget_ratio,
                    "threshold": model.threshold,
                    "rank": rank,
                    "source": relation.source,
                    "tier": _source_tier(relation.source, track),
                    "selected_lag": relation.lag,
                    "weight": relation.weight,
                    "score": relation.score,
                    "sample_count": relation.sample_count,
                }
            )


def _tier_counts(relations, track):
    counts = {
        "strong_retained": 0,
        "medium_retained": 0,
        "weak_retained": 0,
        "noise_retained": 0,
    }
    for relation in relations:
        counts[f"{_source_tier(relation.source, track)}_retained"] += 1
    return counts


def _source_tier(source, track):
    if track == "resource_stress":
        return source_tier(source)
    if source == "driver_a":
        return "strong"
    if source == "driver_b":
        return "medium"
    if source == "noise":
        return "noise"
    raise ValueError(f"unknown low-dimensional source: {source!r}")


def _summarize_by_track_budget(rows):
    grouped = {}
    for row in rows:
        grouped.setdefault((row["track"], row["budget_ratio"]), []).append(row)

    summaries = []
    for (track, budget_ratio) in sorted(grouped, key=lambda key: (key[0], -key[1])):
        group = grouped[(track, budget_ratio)]
        summaries.append(
            {
                "track": track,
                "budget_ratio": budget_ratio,
                "threshold": group[0]["threshold"],
                "runs": len(group),
                **_summary_values(group, "retained_relation_count"),
                **_summary_values(group, "downstream_compute_reduction_pct"),
                **_summary_values(group, "downstream_memory_reduction_pct"),
                **_summary_values(group, "mae"),
                **_summary_values(group, "rmse"),
                **_summary_values(group, "mae_loss_pct"),
                **_summary_values(group, "rmse_loss_pct"),
                **_summary_values(group, "strong_retained"),
                **_summary_values(group, "medium_retained"),
                **_summary_values(group, "weak_retained"),
                **_summary_values(group, "noise_retained"),
            }
        )
    return summaries


def _summary_values(rows, key):
    values = [float(row[key]) for row in rows]
    return {
        f"{key}_mean": mean(values),
        f"{key}_min": min(values),
        f"{key}_max": max(values),
    }


def _write_metrics(rows, path: Path) -> None:
    fieldnames = [
        "track",
        "seed",
        "budget_ratio",
        "threshold",
        "retained_relation_count",
        "retained_feature_count",
        "downstream_compute_proxy",
        "downstream_memory_proxy",
        "estimated_memory_bytes",
        "downstream_compute_reduction_pct",
        "downstream_memory_reduction_pct",
        "mae",
        "rmse",
        "mae_loss_pct",
        "rmse_loss_pct",
        "strong_retained",
        "medium_retained",
        "weak_retained",
        "noise_retained",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    **row,
                    "budget_ratio": f"{row['budget_ratio']:.2f}",
                    "threshold": f"{row['threshold']:.10f}",
                    "downstream_compute_reduction_pct": f"{row['downstream_compute_reduction_pct']:.10f}",
                    "downstream_memory_reduction_pct": f"{row['downstream_memory_reduction_pct']:.10f}",
                    "mae": f"{row['mae']:.10f}",
                    "rmse": f"{row['rmse']:.10f}",
                    "mae_loss_pct": f"{row['mae_loss_pct']:.10f}",
                    "rmse_loss_pct": f"{row['rmse_loss_pct']:.10f}",
                }
            )


def _write_retention(rows, path: Path) -> None:
    fieldnames = [
        "track",
        "seed",
        "budget_ratio",
        "threshold",
        "rank",
        "source",
        "tier",
        "selected_lag",
        "weight",
        "score",
        "sample_count",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    **row,
                    "budget_ratio": f"{row['budget_ratio']:.2f}",
                    "threshold": f"{row['threshold']:.10f}",
                    "weight": f"{row['weight']:.10f}",
                    "score": f"{row['score']:.10f}",
                }
            )


def _write_summary(rows, path: Path) -> None:
    lines = [
        "# Sprint 5 Resource-Adaptive Ignore Summary",
        "",
        "Protocol: deterministic five-budget scan over two tracks. The S4 frozen drift data is used as a correctness regression; the new high-dimensional fixture is used only for resource stress.",
        "",
        "`BENCHMARK_NOISE_FLOOR = 0.06` is the observed benchmark floor from the current frozen synthetic setup with max-over-lag relation scoring. It is not a universal statistical threshold for real data.",
        "",
        "Threshold rule: `threshold = MIN_THRESHOLD + (1 - budget_ratio) * (MAX_THRESHOLD - MIN_THRESHOLD)`, with `MAX_PRESSURE_THRESHOLD = 0.50`.",
        "",
        "Resource metrics are downstream proxies after relation discovery. They do not claim end-to-end compute reduction because all candidate relations are still scored before ignoring.",
        "",
    ]
    for track in sorted({row["track"] for row in rows}):
        lines.extend(
            [
                f"## {track}",
                "",
                "| Budget ratio | Threshold | Retained relations mean | Retained range | Downstream compute reduction mean | Downstream memory reduction mean | MAE mean | MAE loss mean | RMSE mean | RMSE loss mean | Tier retention mean |",
                "|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|",
            ]
        )
        for row in [item for item in rows if item["track"] == track]:
            lines.append(
                "| {budget_ratio:.2f} | {threshold:.2f} | {retained_relation_count_mean:.2f} | "
                "{retained_relation_count_min:.0f}-{retained_relation_count_max:.0f} | "
                "{downstream_compute_reduction_pct_mean:.2f}% | "
                "{downstream_memory_reduction_pct_mean:.2f}% | "
                "{mae_mean:.6f} | {mae_loss_pct_mean:.2f}% | "
                "{rmse_mean:.6f} | {rmse_loss_pct_mean:.2f}% | "
                "S {strong_retained_mean:.1f} / M {medium_retained_mean:.1f} / W {weak_retained_mean:.1f} / N {noise_retained_mean:.1f} |".format(
                    **row
                )
            )
        lines.append("")
    lines.extend(
        [
            "## Acceptance Notes",
            "",
            "- As `budget_ratio` falls, threshold rises monotonically by construction.",
            "- Retained relation counts and downstream proxies are expected to be monotonic non-increasing within each seed because the same train-only weight ranking is filtered by higher thresholds.",
            "- The full per-seed retention table is tracked in `reports/resource_adaptive_retention.csv`.",
            "- Actual wall-clock time is intentionally not an acceptance metric because local machine load is not byte-reproducible.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _reduction(value, baseline):
    if baseline == 0:
        return 0.0
    return (1.0 - value / baseline) * 100.0


def _increase(value, baseline):
    if baseline == 0:
        return 0.0
    return (value - baseline) / baseline * 100.0


if __name__ == "__main__":
    raise SystemExit(main())
