#!/usr/bin/env python3
"""Run S10 Evidence Gate and Prediction Confidence reports."""

from __future__ import annotations

import csv
import sys
from pathlib import Path
from typing import Dict, List, Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from nestor_delta.evidence_gate import select_relations_with_evidence  # noqa: E402
from nestor_delta.relation_weights import RelationWeight  # noqa: E402
from nestor_delta.s10_fixtures import (  # noqa: E402
    confidence_calibration_fixture,
    fixture_d_runs,
    fixture_d_summary,
)

REPORT_ROOT = REPO_ROOT / "reports"


def main() -> int:
    REPORT_ROOT.mkdir(parents=True, exist_ok=True)
    fixture_d_path = REPORT_ROOT / "s10_fixture_d_selection_quality.csv"
    confidence_path = REPORT_ROOT / "s10_confidence_calibration.csv"
    summary_path = REPORT_ROOT / "s10_evidence_confidence_summary.md"

    fixture_d_rows = _fixture_d_rows()
    confidence_rows = _confidence_rows()
    fallback_status = _fallback_status()

    _write_csv(fixture_d_path, fixture_d_rows)
    _write_csv(confidence_path, confidence_rows)
    _write_summary(summary_path, fixture_d_rows, confidence_rows, fallback_status)

    for path in (fixture_d_path, confidence_path, summary_path):
        print(f"Wrote {path}")
    return 0


def _fixture_d_rows() -> List[Dict[str, object]]:
    rows: List[Dict[str, object]] = []
    for run in fixture_d_runs():
        rows.append(
            {
                "fixture": "fixture_d_mixed_true_pseudo_dead",
                "seed": run.seed,
                "fixed_threshold_precision": run.fixed_precision,
                "fixed_threshold_recall": run.fixed_recall,
                "evidence_gate_precision": run.gate_precision,
                "evidence_gate_recall": run.gate_recall,
                "fixed_selected_count": run.fixed_selected_count,
                "gate_selected_count": run.gate_selected_count,
            }
        )
    return rows


def _confidence_rows() -> List[Dict[str, object]]:
    calibration = confidence_calibration_fixture()
    return [
        {
            "bin": index + 1,
            "mean_confidence": mean_confidence,
            "mean_abs_error": mean_abs_error,
            "count": count,
            "rank_correlation_confidence_vs_abs_error": calibration.rank_correlation,
        }
        for index, (mean_confidence, mean_abs_error, count) in enumerate(calibration.bins)
    ]


def _fallback_status() -> str:
    weak = RelationWeight(
        source="weak_real_data_candidate",
        target="target",
        lag=1,
        weight=0.05,
        score=0.05,
        sample_count=120,
        transform="diff",
        stability=0.10,
        uncertainty=0.30,
    )
    return select_relations_with_evidence((weak,), max_lag=3).fit_status


def _write_csv(path: Path, rows: Sequence[Dict[str, object]]) -> None:
    if not rows:
        raise ValueError(f"no rows for {path}")
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=tuple(rows[0].keys()), lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(rows)


def _write_summary(
    path: Path,
    fixture_d_rows: Sequence[Dict[str, object]],
    confidence_rows: Sequence[Dict[str, object]],
    fallback_status: str,
) -> None:
    summary = fixture_d_summary()
    rank_correlation = float(
        confidence_rows[0]["rank_correlation_confidence_vs_abs_error"]
    )
    lowest_error = float(confidence_rows[0]["mean_abs_error"])
    highest_error = float(confidence_rows[-1]["mean_abs_error"])
    lines = [
        "# S10 Evidence Gate and Prediction Confidence v0",
        "",
        "Scope: S10 only. Evidence Gate consumes relation evidence; Prediction Confidence is reported separately and does not feed back into selection.",
        "",
        "Selection inputs: effect size against the S8 noise floor, S9 stability, relationship uncertainty, sample support, and FDR correction across relations/lags.",
        "",
        "Forbidden path remains absent: prediction error is not an input to selection.",
        "",
        "## Fixture D: Selection Quality",
        "",
        f"- Seeds: `{summary.seed_count}`",
        f"- Fixed threshold precision mean: `{summary.fixed_precision_mean:.3f}`",
        f"- Fixed threshold recall mean: `{summary.fixed_recall_mean:.3f}`",
        f"- Evidence Gate precision mean: `{summary.gate_precision_mean:.3f}`",
        f"- Evidence Gate recall mean: `{summary.gate_recall_mean:.3f}`",
        f"- Precision lift: `{summary.precision_lift:.3f}`",
        f"- Recall lift: `{summary.recall_lift:.3f}`",
        "",
        "## Prediction Confidence Calibration",
        "",
        f"- Spearman rank correlation, confidence vs absolute error: `{rank_correlation:.3f}`",
        f"- Lowest-confidence bin mean absolute error: `{lowest_error:.3f}`",
        f"- Highest-confidence bin mean absolute error: `{highest_error:.3f}`",
        "",
        "## Baseline Fallback",
        "",
        f"- No-evidence relation set fit status: `{fallback_status}`",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
