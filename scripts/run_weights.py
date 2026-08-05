#!/usr/bin/env python3
"""Run Sprint 2 relation-weight validation on frozen synthetic data."""

from __future__ import annotations

import csv
import sys
from pathlib import Path
from statistics import mean

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from nestor_delta.config import FEATURE_COLUMNS, LAG_WINDOW, SEEDS  # noqa: E402
from nestor_delta.relation_weights import (  # noqa: E402
    compute_lagged_relation_weights,
    rank_target_sources,
)
from nestor_delta.synthetic import generate_series  # noqa: E402


def main() -> int:
    reports_dir = REPO_ROOT / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    rows = []
    for seed in SEEDS:
        series = generate_series(seed)
        weights = compute_lagged_relation_weights(series, FEATURE_COLUMNS, LAG_WINDOW)
        ranked_target_sources = rank_target_sources(weights, "target")
        for rank, weight in enumerate(ranked_target_sources, start=1):
            rows.append(
                {
                    "seed": seed,
                    "target": weight.target,
                    "source": weight.source,
                    "rank": rank,
                    "lag": weight.lag,
                    "weight": weight.weight,
                    "score": weight.score,
                    "sample_count": weight.sample_count,
                }
            )

    detail_path = reports_dir / "weight_validation.csv"
    with detail_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "seed",
                "target",
                "source",
                "rank",
                "lag",
                "weight",
                "score",
                "sample_count",
            ],
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "seed": row["seed"],
                    "target": row["target"],
                    "source": row["source"],
                    "rank": row["rank"],
                    "lag": row["lag"],
                    "weight": f"{row['weight']:.10f}",
                    "score": f"{row['score']:.10f}",
                    "sample_count": row["sample_count"],
                }
            )

    summary_rows = _summarize(rows)
    summary_path = reports_dir / "weight_validation_summary.md"
    _write_summary(summary_rows, summary_path)

    print("Wrote reports/weight_validation.csv")
    print("Wrote reports/weight_validation_summary.md")
    for row in summary_rows:
        print(
            "{source}: mean_rank={mean_rank:.2f} rank_range={min_rank}-{max_rank}; "
            "mean_score={mean_score:.6f} score_range={min_score:.6f}-{max_score:.6f}".format(
                **row
            )
        )
    return 0


def _summarize(rows):
    by_source = {}
    for row in rows:
        by_source.setdefault(row["source"], []).append(row)

    summaries = []
    for source in sorted(by_source):
        source_rows = by_source[source]
        ranks = [row["rank"] for row in source_rows]
        scores = [row["score"] for row in source_rows]
        summaries.append(
            {
                "source": source,
                "runs": len(source_rows),
                "mean_rank": mean(ranks),
                "min_rank": min(ranks),
                "max_rank": max(ranks),
                "mean_score": mean(scores),
                "min_score": min(scores),
                "max_score": max(scores),
            }
        )
    return summaries


def _write_summary(summary_rows, path: Path) -> None:
    lines = [
        "# Sprint 2 Relation Weight Validation",
        "",
        "Protocol: layer-independent lagged Pearson relation weights over the five frozen synthetic seeds.",
        "",
        "Rows summarize source variables ranked for target `target`. Ranges are min-max.",
        "",
        "| Source | Runs | Mean rank | Rank range | Mean score | Score range |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for row in summary_rows:
        lines.append(
            "| {source} | {runs} | {mean_rank:.2f} | {min_rank}-{max_rank} | "
            "{mean_score:.6f} | {min_score:.6f}-{max_score:.6f} |".format(**row)
        )
    lines.extend(
        [
            "",
            "Acceptance check: known drivers `driver_a` and `driver_b` should rank ahead of `noise` for `target` across the frozen seeds.",
            "This script validates the standalone weighting mechanism only; it does not run weighted prediction.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
