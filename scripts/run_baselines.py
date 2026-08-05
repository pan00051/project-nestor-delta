#!/usr/bin/env python3
"""Generate synthetic data and run Sprint 1 baselines."""

from __future__ import annotations

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
from nestor_delta.reporting import (  # noqa: E402
    summarize_metrics,
    write_metrics_csv,
    write_summary_markdown,
)
from nestor_delta.splits import build_lagged_samples  # noqa: E402
from nestor_delta.synthetic import generate_series, write_series_csv  # noqa: E402


def main() -> int:
    data_dir = REPO_ROOT / "data" / "synthetic"
    reports_dir = REPO_ROOT / "reports"

    metric_rows = []
    for seed in SEEDS:
        rows = generate_series(seed)
        write_series_csv(rows, data_dir / f"synthetic_seed_{seed}.csv")

        train_features, train_labels = build_lagged_samples(rows, TRAIN_LABEL_ROWS)
        test_features, test_labels = build_lagged_samples(rows, TEST_LABEL_ROWS)

        persistence_predictions = predict_persistence(rows, TEST_LABEL_ROWS)
        metric_rows.append(
            {
                "baseline": "persistence",
                "seed": float(seed),
                "split": "test",
                "mae": mae(test_labels, persistence_predictions),
                "rmse": rmse(test_labels, persistence_predictions),
                "sample_count": float(len(test_labels)),
            }
        )

        coefficients = fit_linear_regression(train_features, train_labels)
        linear_predictions = predict_linear_regression(test_features, coefficients)
        metric_rows.append(
            {
                "baseline": "linear_regression",
                "seed": float(seed),
                "split": "test",
                "mae": mae(test_labels, linear_predictions),
                "rmse": rmse(test_labels, linear_predictions),
                "sample_count": float(len(test_labels)),
            }
        )

    summaries = summarize_metrics(metric_rows)
    write_metrics_csv(metric_rows, reports_dir / "baseline_metrics.csv")
    write_summary_markdown(summaries, reports_dir / "baseline_summary.md")

    print("Wrote data/synthetic/synthetic_seed_<seed>.csv")
    print("Wrote reports/baseline_metrics.csv")
    print("Wrote reports/baseline_summary.md")
    for row in summaries:
        print(
            "{baseline}: MAE mean={mae_mean:.6f} range={mae_min:.6f}-{mae_max:.6f}; "
            "RMSE mean={rmse_mean:.6f} range={rmse_min:.6f}-{rmse_max:.6f}".format(**row)
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
