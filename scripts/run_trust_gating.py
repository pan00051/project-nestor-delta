#!/usr/bin/env python3
"""Compare frozen Sprint 3 OLS with pre-OLS trust gating."""

from __future__ import annotations

import csv
import sys
from dataclasses import replace
from pathlib import Path
from statistics import mean

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from nestor_delta.baselines import (  # noqa: E402
    fit_linear_regression,
    predict_linear_regression,
)
from nestor_delta.config import (  # noqa: E402
    FEATURE_COLUMNS,
    LAG_WINDOW,
    SEEDS,
    TEST_LABEL_ROWS,
    TRAIN_LABEL_ROWS,
)
from nestor_delta.metrics import mae, rmse  # noqa: E402
from nestor_delta.relation_weights import (  # noqa: E402
    RelationWeight,
    compute_lagged_relation_weights,
)
from nestor_delta.reporting import summarize_metrics  # noqa: E402
from nestor_delta.stage1_prediction import build_stage1_features  # noqa: E402
from nestor_delta.synthetic import generate_series  # noqa: E402
from nestor_delta.trust_gated_prediction import (  # noqa: E402
    TrustGatedModel,
    fit_prediction_mode,
    fit_trust_gated_predictor,
    predict_trust_gated,
    predict_with_mode,
)
from nestor_delta.trust_gating import DEFAULT_GATE_CONFIG  # noqa: E402


def main() -> int:
    reports_dir = REPO_ROOT / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    metric_rows = []
    admission_rows = []
    sensitivity_rows = []

    for seed in SEEDS:
        rows = generate_series(seed)
        labels = [float(rows[index]["target"]) for index in TEST_LABEL_ROWS]
        train_history = rows[: max(TRAIN_LABEL_ROWS) + 1]
        relation_weights = compute_lagged_relation_weights(
            train_history, FEATURE_COLUMNS, LAG_WINDOW
        )
        stronger_weak_source_weights = [
            _with_source_unit_trust(weight, "driver_b")
            for weight in relation_weights
        ]

        ols_model = fit_prediction_mode(rows, TRAIN_LABEL_ROWS, "ols")
        ols_predictions = predict_with_mode(
            rows, TEST_LABEL_ROWS, ols_model, "ols"
        )
        metric_rows.append(_metric_row("sprint3_ols", seed, labels, ols_predictions))

        gated_model = fit_prediction_mode(rows, TRAIN_LABEL_ROWS, "trust_gated")
        if not isinstance(gated_model, TrustGatedModel):
            raise TypeError("trust_gated mode returned the wrong model type")
        gated_predictions = predict_with_mode(
            rows, TEST_LABEL_ROWS, gated_model, "trust_gated"
        )
        metric_rows.append(
            _metric_row("trust_gated_ols", seed, labels, gated_predictions)
        )

        for rank, gate in enumerate(gated_model.gates, start=1):
            admission_rows.append(
                {
                    "seed": seed,
                    "rank": rank,
                    "source": gate.source,
                    "selected_lag": gate.lag,
                    "direction": gate.direction,
                    "trust": gate.trust,
                    "admission": gate.admission,
                    "blocked": gate.admission == 0.0,
                    "sample_count": gate.sample_count,
                }
            )

        ols_unit_predictions = _predict_stage1_with_weights(
            rows,
            tuple(
                _with_source_unit_trust(weight, "driver_b")
                for weight in ols_model.selected_weights
            ),
        )
        sensitivity_rows.append(
            _sensitivity_row(
                "sprint3_ols",
                seed,
                "driver_b_unit_trust",
                ols_predictions,
                ols_unit_predictions,
            )
        )

        gated_unit_model = fit_trust_gated_predictor(
            rows,
            TRAIN_LABEL_ROWS,
            relation_weights=stronger_weak_source_weights,
        )
        gated_unit_predictions = predict_trust_gated(
            rows, TEST_LABEL_ROWS, gated_unit_model
        )
        sensitivity_rows.append(
            _sensitivity_row(
                "trust_gated_ols",
                seed,
                "driver_b_unit_trust",
                gated_predictions,
                gated_unit_predictions,
            )
        )

    summaries = summarize_metrics(metric_rows)
    sensitivity_summaries = _summarize_sensitivity(sensitivity_rows)
    admission_summaries = _summarize_admissions(admission_rows)

    _write_metrics(metric_rows, reports_dir / "trust_gating_metrics.csv")
    _write_admissions(admission_rows, reports_dir / "trust_gating_admissions.csv")
    _write_sensitivity(
        sensitivity_rows, reports_dir / "trust_gating_sensitivity.csv"
    )
    _write_summary(
        summaries,
        admission_summaries,
        sensitivity_summaries,
        reports_dir / "trust_gating_summary.md",
    )

    print("Wrote reports/trust_gating_metrics.csv")
    print("Wrote reports/trust_gating_admissions.csv")
    print("Wrote reports/trust_gating_sensitivity.csv")
    print("Wrote reports/trust_gating_summary.md")
    for row in summaries:
        print(
            "{baseline}: MAE mean={mae_mean:.6f} range={mae_min:.6f}-{mae_max:.6f}; "
            "RMSE mean={rmse_mean:.6f} range={rmse_min:.6f}-{rmse_max:.6f}".format(
                **row
            )
        )
    for row in sensitivity_summaries:
        print(
            "{mode} driver_b-unit-trust prediction delta: mean={delta_mean:.10f} "
            "range={delta_min:.10f}-{delta_max:.10f}".format(**row)
        )
    return 0


def _metric_row(method, seed, labels, predictions):
    return {
        "baseline": method,
        "seed": float(seed),
        "split": "test",
        "mae": mae(labels, predictions),
        "rmse": rmse(labels, predictions),
        "sample_count": float(len(labels)),
    }


def _with_source_unit_trust(
    weight: RelationWeight, source: str
) -> RelationWeight:
    if weight.source != source or weight.target != "target":
        return weight
    direction = -1.0 if weight.weight < 0.0 else 1.0
    return replace(weight, weight=direction, score=1.0)


def _predict_stage1_with_weights(rows, selected_weights):
    train_features, train_labels = build_stage1_features(
        rows, TRAIN_LABEL_ROWS, selected_weights
    )
    test_features, _ = build_stage1_features(
        rows, TEST_LABEL_ROWS, selected_weights
    )
    coefficients = fit_linear_regression(train_features, train_labels)
    return predict_linear_regression(test_features, coefficients)


def _sensitivity_row(mode, seed, perturbation, original, changed):
    deltas = [abs(left - right) for left, right in zip(original, changed)]
    return {
        "mode": mode,
        "seed": seed,
        "perturbation": perturbation,
        "mean_abs_prediction_delta": mean(deltas),
        "max_abs_prediction_delta": max(deltas),
        "sample_count": len(deltas),
    }


def _summarize_sensitivity(rows):
    grouped = {}
    for row in rows:
        grouped.setdefault(row["mode"], []).append(row)
    summaries = []
    for mode in sorted(grouped):
        values = [row["mean_abs_prediction_delta"] for row in grouped[mode]]
        summaries.append(
            {
                "mode": mode,
                "runs": len(values),
                "delta_mean": mean(values),
                "delta_min": min(values),
                "delta_max": max(values),
            }
        )
    return summaries


def _summarize_admissions(rows):
    grouped = {}
    for row in rows:
        grouped.setdefault(row["source"], []).append(row)
    summaries = []
    for source in sorted(grouped):
        source_rows = grouped[source]
        trusts = [row["trust"] for row in source_rows]
        admissions = [row["admission"] for row in source_rows]
        directions = {int(row["direction"]) for row in source_rows}
        summaries.append(
            {
                "source": source,
                "runs": len(source_rows),
                "direction": (
                    f"{next(iter(directions)):+d}" if len(directions) == 1 else "mixed"
                ),
                "trust_mean": mean(trusts),
                "trust_min": min(trusts),
                "trust_max": max(trusts),
                "admission_mean": mean(admissions),
                "admission_min": min(admissions),
                "admission_max": max(admissions),
                "blocked_runs": sum(row["blocked"] for row in source_rows),
            }
        )
    return summaries


def _write_metrics(rows, path: Path) -> None:
    fieldnames = ["baseline", "seed", "split", "mae", "rmse", "sample_count"]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "baseline": row["baseline"],
                    "seed": int(row["seed"]),
                    "split": row["split"],
                    "mae": f"{float(row['mae']):.10f}",
                    "rmse": f"{float(row['rmse']):.10f}",
                    "sample_count": int(row["sample_count"]),
                }
            )


def _write_admissions(rows, path: Path) -> None:
    fieldnames = [
        "seed",
        "rank",
        "source",
        "selected_lag",
        "direction",
        "trust",
        "admission",
        "blocked",
        "sample_count",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    **row,
                    "direction": int(row["direction"]),
                    "trust": f"{row['trust']:.10f}",
                    "admission": f"{row['admission']:.10f}",
                    "blocked": str(row["blocked"]).lower(),
                }
            )


def _write_sensitivity(rows, path: Path) -> None:
    fieldnames = [
        "mode",
        "seed",
        "perturbation",
        "mean_abs_prediction_delta",
        "max_abs_prediction_delta",
        "sample_count",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    **row,
                    "mean_abs_prediction_delta": (
                        f"{row['mean_abs_prediction_delta']:.10f}"
                    ),
                    "max_abs_prediction_delta": f"{row['max_abs_prediction_delta']:.10f}",
                }
            )


def _write_summary(metrics, admissions, sensitivity, path: Path) -> None:
    by_method = {row["baseline"]: row for row in metrics}
    ols = by_method["sprint3_ols"]
    gated = by_method["trust_gated_ols"]
    mae_tradeoff = (gated["mae_mean"] - ols["mae_mean"]) / ols["mae_mean"] * 100.0
    rmse_tradeoff = (
        (gated["rmse_mean"] - ols["rmse_mean"]) / ols["rmse_mean"] * 100.0
    )

    lines = [
        "# Trust-Gating Prediction Summary",
        "",
        "Protocol: `EVALUATION.md` v1 frozen split, five seeds, and test MAE/RMSE.",
        "",
        "Default gate: trust `<= 0.15` is blocked, trust `>= 0.50` is fully admitted, and values between them use linear admission.",
        "Direction is stored separately from absolute trust. Gated sources are combined before OLS so the model cannot independently undo their relative admissions.",
        "",
        "## Prediction Comparison",
        "",
        "| Mode | Runs | MAE mean | MAE range | RMSE mean | RMSE range |",
        "|---|---:|---:|---:|---:|---:|",
    ]
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
            f"Trade-off: trust gating has {mae_tradeoff:.2f}% higher mean MAE and {rmse_tradeoff:.2f}% higher mean RMSE than the frozen Sprint 3 OLS mode.",
            "It still beats persistence, but this experiment is about making trust numerically operative, not claiming a guaranteed accuracy gain.",
            "",
            "## Gate Admissions",
            "",
            "| Source | Runs | Direction | Trust mean | Trust range | Admission mean | Admission range | Blocked runs |",
            "|---|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in admissions:
        lines.append(
            "| {source} | {runs} | {direction} | {trust_mean:.6f} | "
            "{trust_min:.6f}-{trust_max:.6f} | {admission_mean:.6f} | "
            "{admission_min:.6f}-{admission_max:.6f} | {blocked_runs} |".format(
                **row
            )
        )
    lines.extend(
        [
            "",
            "## Weight Sensitivity Check",
            "",
            "Counterfactual: preserve every relation's direction and selected lag, change only `driver_b` trust to `1.0`, and refit on the same train samples. Noise remains blocked.",
            "",
            "| Mode | Runs | Mean prediction delta | Per-seed range |",
            "|---|---:|---:|---:|",
        ]
    )
    for row in sensitivity:
        lines.append(
            "| {mode} | {runs} | {delta_mean:.10f} | "
            "{delta_min:.10f}-{delta_max:.10f} |".format(**row)
        )
    lines.extend(
        [
            "",
            "The Sprint 3 OLS delta is numerical roundoff: independent non-zero feature scaling is re-estimated away.",
            "The gated delta is material because trust changes the composition of the shared relation signal before OLS; blocked information cannot be reconstructed from separate source columns.",
            "",
            "## Boundary",
            "",
            "This is a static, deterministic trust-gating experiment. It does not implement dynamic weights, threshold tuning, resource adaptation, or causal attribution.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
