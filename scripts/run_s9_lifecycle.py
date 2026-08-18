#!/usr/bin/env python3
"""Run S9 temporal stability and lifecycle acceptance reports."""

from __future__ import annotations

import csv
import sys
from pathlib import Path
from statistics import median
from typing import Dict, List, Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from nestor_delta.s9_fixtures import (  # noqa: E402
    FIXTURE_C_DEATH_STEP,
    FIXTURE_C_K,
    FIXTURE_C_SEEDS,
    fixture_a_transformed_lifecycle_states,
    fixture_a_transformed_stability_scores,
    fixture_c_detection_lags,
)

REPORT_ROOT = REPO_ROOT / "reports"


def main() -> int:
    REPORT_ROOT.mkdir(parents=True, exist_ok=True)
    fixture_c_path = REPORT_ROOT / "s9_fixture_c_detection_lags.csv"
    fixture_a_path = REPORT_ROOT / "s9_fixture_a_stability_regression.csv"
    summary_path = REPORT_ROOT / "s9_relation_lifecycle_summary.md"

    fixture_c_rows = _fixture_c_rows()
    fixture_a_rows = _fixture_a_rows()

    _write_csv(fixture_c_path, fixture_c_rows)
    _write_csv(fixture_a_path, fixture_a_rows)
    _write_summary(summary_path, fixture_c_rows, fixture_a_rows)

    for path in (fixture_c_path, fixture_a_path, summary_path):
        print(f"Wrote {path}")
    return 0


def _fixture_c_rows() -> List[Dict[str, object]]:
    lags = fixture_c_detection_lags(seeds=FIXTURE_C_SEEDS, k_steps=FIXTURE_C_K)
    rows: List[Dict[str, object]] = []
    for seed, lag in zip(FIXTURE_C_SEEDS, lags):
        rows.append(
            {
                "fixture": "fixture_c_relation_death",
                "path": "s7_transformed_diff_rolling",
                "seed": seed,
                "death_step": FIXTURE_C_DEATH_STEP,
                "k_steps": FIXTURE_C_K,
                "detection_lag": "" if lag is None else lag,
                "detected_within_k": str(lag is not None).lower(),
            }
        )
    return rows


def _fixture_a_rows() -> List[Dict[str, object]]:
    scores = fixture_a_transformed_stability_scores(seeds=tuple(range(100)))
    states = fixture_a_transformed_lifecycle_states(seeds=tuple(range(100)))
    endorsed_count = sum(state in {"stable", "strengthening"} for state in states)
    return [
        {
            "fixture": "fixture_a_random_walk",
            "path": "s7_transformed_diff_rolling",
            "seed_count": len(scores),
            "median_stability": median(scores),
            "p90_stability": _quantile(scores, 0.9),
            "max_stability": max(scores),
            "pass_rate_stability_gt_045": sum(score > 0.45 for score in scores)
            / len(scores),
            "state_distribution": _state_distribution(states),
            "endorsed_state_count": endorsed_count,
            "endorsed_state_rate": endorsed_count / len(states),
        }
    ]


def _write_csv(path: Path, rows: Sequence[Dict[str, object]]) -> None:
    if not rows:
        raise ValueError(f"no rows for {path}")
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=tuple(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _write_summary(
    path: Path,
    fixture_c_rows: Sequence[Dict[str, object]],
    fixture_a_rows: Sequence[Dict[str, object]],
) -> None:
    detected_lags = [
        int(row["detection_lag"])
        for row in fixture_c_rows
        if row["detection_lag"] != ""
    ]
    fixture_a = fixture_a_rows[0]
    lines = [
        "# S9 Temporal Stability and Relation Lifecycle",
        "",
        "Scope: S9 only. Stability and lifecycle are computed from S7 transformed rolling relation trajectories, not from legacy level Pearson scores.",
        "",
        "No S10 Evidence Gate, Prediction Confidence, or prediction-error feedback into selection is implemented here.",
        "",
        "## Relation Object v1",
        "",
        "`RelationWeight` keeps existing `source, target, lag, weight, score, sample_count, transform` fields and adds only `stability`, `uncertainty`, and `selected`.",
        "",
        "The `selected` field is nullable in S9. This report does not infer model selection.",
        "",
        "## Fixture C: Relation Death Detection",
        "",
        f"- Seeds: `{len(fixture_c_rows)}`",
        f"- Known death step: `{FIXTURE_C_DEATH_STEP}`",
        f"- K-step window: `{FIXTURE_C_K}`",
        f"- Detected within K: `{len(detected_lags)}/{len(fixture_c_rows)}`",
        f"- Median detection lag: `{median(detected_lags):.1f}`",
        f"- Detection lag distribution: `{_distribution(detected_lags)}`",
        "",
        "## Fixture A Regression",
        "",
        "Independent random walks are measured through the S7 transformed path before S9 aggregation.",
        "",
        f"- Median stability: `{float(fixture_a['median_stability']):.3f}`",
        f"- P90 stability: `{float(fixture_a['p90_stability']):.3f}`",
        f"- Max stability: `{float(fixture_a['max_stability']):.3f}`",
        f"- P(stability > 0.45): `{float(fixture_a['pass_rate_stability_gt_045']):.1%}`",
        f"- Lifecycle state distribution: `{fixture_a['state_distribution']}`",
        f"- P(state in stable/strengthening): `{float(fixture_a['endorsed_state_rate']):.1%}`",
        "",
        "## Lifecycle States",
        "",
        "`birth -> strengthening -> stable -> decaying -> dead` is implemented in `temporal_stability.py` from relation-score trajectory shape only.",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def _quantile(values: Sequence[float], quantile: float) -> float:
    ordered = sorted(values)
    index = int(quantile * (len(ordered) - 1))
    return ordered[index]


def _distribution(values: Sequence[int]) -> str:
    counts: Dict[int, int] = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1
    return ", ".join(f"{value}:{counts[value]}" for value in sorted(counts))


def _state_distribution(values: Sequence[str]) -> str:
    counts: Dict[str, int] = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1
    return ", ".join(f"{value}:{counts[value]}" for value in sorted(counts))


if __name__ == "__main__":
    raise SystemExit(main())
