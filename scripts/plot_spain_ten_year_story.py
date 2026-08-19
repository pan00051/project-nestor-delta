#!/usr/bin/env python3
"""Build an exploratory ten-year story chart from the frozen Spain case."""

from __future__ import annotations

import csv
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import matplotlib

matplotlib.use("Agg")
matplotlib.rcParams["svg.hashsalt"] = "nestor-delta-spain-ten-year-story"

import matplotlib.dates as mdates
import matplotlib.pyplot as plt

from nestor_delta.metrics import mae
from nestor_delta.real_data import load_real_case_config, load_real_case_data
from nestor_delta.relation_weights import (
    RelationWeight,
    compute_lagged_relation_weights,
    rank_target_sources,
)
from nestor_delta.resource_adaptive_ignore import threshold_for_budget


CASE_NAME = "spain_retail_eurostat_2008_2025"
CASE_DIR = ROOT / "cases" / CASE_NAME
REPORT_DIR = ROOT / "reports" / CASE_NAME

CONFIG_PATH = CASE_DIR / "case.json"
FROZEN_PREDICTIONS_PATH = REPORT_DIR / "real_budget_sweep_predictions.csv"
FROZEN_METRICS_PATH = REPORT_DIR / "real_budget_sweep_metrics.csv"

SERIES_PATH = REPORT_DIR / "ten_year_story_series.csv"
WEIGHTS_PATH = REPORT_DIR / "ten_year_story_weights.csv"
FIGURE_PATH = REPORT_DIR / "ten_year_story.png"
SVG_PATH = REPORT_DIR / "ten_year_story.svg"

DISPLAY_START = "2016-01"
DISPLAY_END = "2025-12"
FORECAST_START = "2024-01"
STORY_BUDGET_RATIO = 0.50

NAVY = "#102A43"
TEAL = "#007C83"
BLUE = "#3E6FB0"
CORAL = "#D95040"
ORANGE = "#D99000"
GRAY = "#8A99A8"
LIGHT_GRAY = "#D9E1E7"
PALE_TEAL = "#EAF6F5"
INK = "#17212B"
MUTED = "#627181"
WHITE = "#FFFFFF"

SOURCE_ORDER = (
    "industrial_production",
    "unemployment_rate",
    "consumer_confidence",
    "hicp",
)
SOURCE_LABELS = {
    "industrial_production": "Industrial production",
    "unemployment_rate": "Unemployment",
    "consumer_confidence": "Consumer confidence",
    "hicp": "HICP (inflation)",
}
SOURCE_COLORS = {
    "industrial_production": TEAL,
    "unemployment_rate": BLUE,
    "consumer_confidence": ORANGE,
    "hicp": CORAL,
}


def _month(value: str) -> datetime:
    return datetime.strptime(value, "%Y-%m")


def _stable_target_ranking(
    weights: Sequence[RelationWeight], target: str
) -> Tuple[RelationWeight, ...]:
    return tuple(
        sorted(
            rank_target_sources(weights, target),
            key=lambda weight: (-weight.score, weight.source, weight.lag),
        )
    )


def _load_frozen_forecast() -> Tuple[Dict[str, float], Tuple[str, ...]]:
    forecasts: Dict[str, float] = {}
    selected_sources: Optional[Tuple[str, ...]] = None
    with FROZEN_PREDICTIONS_PATH.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            if float(row["budget_ratio"]) != STORY_BUDGET_RATIO:
                continue
            date = row["date"]
            forecasts[date] = float(row["delta_prediction"])
            row_sources = tuple(
                source for source in row["actual_ols_sources"].split(";") if source
            )
            if selected_sources is None:
                selected_sources = row_sources
            elif row_sources != selected_sources:
                raise ValueError("frozen forecast source set changes within one tier")
    if len(forecasts) != 24 or selected_sources is None:
        raise ValueError("expected 24 frozen budget-0.50 forecast rows")
    return forecasts, selected_sources


def _load_frozen_metrics() -> Dict[str, float]:
    with FROZEN_METRICS_PATH.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if float(row["budget_ratio"]) == STORY_BUDGET_RATIO:
                return {
                    "persistence_mae": float(row["persistence_mae"]),
                    "delta_mae": float(row["delta_mae"]),
                    "mae_change_pct": float(
                        row["mae_change_vs_persistence_pct"]
                    ),
                }
    raise ValueError("missing frozen budget-0.50 metrics row")


def _rolling_weights(
    dates: Sequence[str],
    rows: Sequence[Dict[str, float]],
    variables: Iterable[str],
    target: str,
    lag_window: int,
) -> List[Dict[str, object]]:
    output: List[Dict[str, object]] = []
    for index, date in enumerate(dates):
        if date < DISPLAY_START or date > DISPLAY_END:
            continue
        history = rows[:index]
        relation_weights = compute_lagged_relation_weights(
            history, variables, lag_window
        )
        ranking = _stable_target_ranking(relation_weights, target)
        by_source = {weight.source: weight for weight in ranking}
        for source in SOURCE_ORDER:
            weight = by_source[source]
            output.append(
                {
                    "date": date,
                    "source": source,
                    "lag": weight.lag,
                    "signed_weight": weight.weight,
                    "absolute_score": weight.score,
                    "sample_count": weight.sample_count,
                    "history_end_exclusive": date,
                }
            )
    return output


def _story_series(
    dates: Sequence[str],
    rows: Sequence[Dict[str, float]],
    target: str,
    forecasts: Dict[str, float],
) -> List[Dict[str, object]]:
    output: List[Dict[str, object]] = []
    for index, date in enumerate(dates):
        if date < DISPLAY_START or date > DISPLAY_END:
            continue
        output.append(
            {
                "date": date,
                "actual": float(rows[index][target]),
                "persistence": float(rows[index - 1][target]),
                "delta_prediction": forecasts.get(date),
            }
        )
    return output


def _validate_cutoff(
    rolling_weights: Sequence[Dict[str, object]],
    selected_sources: Tuple[str, ...],
) -> Dict[str, float]:
    cutoff = {
        str(row["source"]): float(row["signed_weight"])
        for row in rolling_weights
        if row["date"] == FORECAST_START
    }
    threshold = threshold_for_budget(STORY_BUDGET_RATIO)
    retained = tuple(
        sorted(
            (source for source, weight in cutoff.items() if abs(weight) > threshold),
            key=lambda source: (-abs(cutoff[source]), source),
        )
    )
    if retained != selected_sources:
        raise ValueError(
            "rolling cutoff weights do not reproduce the frozen selected sources"
        )
    return cutoff


def _write_series(rows: Sequence[Dict[str, object]]) -> None:
    fieldnames = ["date", "actual", "persistence", "delta_prediction"]
    with SERIES_PATH.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "date": row["date"],
                    "actual": f"{float(row['actual']):.10f}",
                    "persistence": f"{float(row['persistence']):.10f}",
                    "delta_prediction": (
                        ""
                        if row["delta_prediction"] is None
                        else f"{float(row['delta_prediction']):.10f}"
                    ),
                }
            )


def _write_weights(rows: Sequence[Dict[str, object]]) -> None:
    fieldnames = [
        "date",
        "source",
        "lag",
        "signed_weight",
        "absolute_score",
        "sample_count",
        "history_end_exclusive",
    ]
    with WEIGHTS_PATH.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "date": row["date"],
                    "source": row["source"],
                    "lag": row["lag"],
                    "signed_weight": f"{float(row['signed_weight']):.10f}",
                    "absolute_score": f"{float(row['absolute_score']):.10f}",
                    "sample_count": row["sample_count"],
                    "history_end_exclusive": row["history_end_exclusive"],
                }
            )


def _style_axis(axis: plt.Axes) -> None:
    axis.set_facecolor(WHITE)
    axis.spines["top"].set_visible(False)
    axis.spines["right"].set_visible(False)
    axis.spines["left"].set_color(GRAY)
    axis.spines["bottom"].set_color(GRAY)
    axis.tick_params(axis="both", colors=INK, labelsize=11.5, length=4)
    axis.grid(axis="y", color=LIGHT_GRAY, linewidth=0.8, alpha=0.55)
    axis.set_axisbelow(True)


def _plot(
    series_rows: Sequence[Dict[str, object]],
    weight_rows: Sequence[Dict[str, object]],
    cutoff_weights: Dict[str, float],
    metrics: Dict[str, float],
) -> None:
    dates = [_month(str(row["date"])) for row in series_rows]
    actuals = [float(row["actual"]) for row in series_rows]
    persistence = [float(row["persistence"]) for row in series_rows]
    forecast_dates = [
        _month(str(row["date"]))
        for row in series_rows
        if row["delta_prediction"] is not None
    ]
    forecasts = [
        float(row["delta_prediction"])
        for row in series_rows
        if row["delta_prediction"] is not None
    ]

    figure = plt.figure(figsize=(15.5, 10.2), dpi=180, facecolor=WHITE)
    grid = figure.add_gridspec(2, 1, height_ratios=(1.25, 1.0), hspace=0.18)
    top = figure.add_subplot(grid[0])
    bottom = figure.add_subplot(grid[1], sharex=top)
    _style_axis(top)
    _style_axis(bottom)

    test_start = _month(FORECAST_START)
    test_end = _month(DISPLAY_END)
    for axis in (top, bottom):
        axis.axvspan(test_start, test_end, color=PALE_TEAL, alpha=0.75, zorder=0)
        axis.axvline(test_start, color=TEAL, linewidth=1.5, linestyle=":", zorder=1)

    top.plot(
        dates,
        actuals,
        color=NAVY,
        linewidth=3.2,
        label="Actual retail sales",
        zorder=4,
    )
    top.plot(
        dates,
        persistence,
        color=GRAY,
        linewidth=1.7,
        linestyle="--",
        label="Persistence: previous month",
        zorder=2,
    )
    top.plot(
        forecast_dates,
        forecasts,
        color=TEAL,
        linewidth=3.0,
        marker="o",
        markersize=3.5,
        markevery=3,
        label="Delta forecast: 2 retained signals",
        zorder=5,
    )
    top.set_ylabel("Retail volume index", fontsize=13.5, color=INK)
    top.legend(
        loc="upper left",
        frameon=False,
        ncol=3,
        fontsize=11.5,
        handlelength=2.6,
    )
    top.text(
        0.012,
        0.87,
        "WHAT HAPPENED?",
        transform=top.transAxes,
        fontsize=11,
        color=MUTED,
        fontweight="bold",
    )
    top.text(
        0.715,
        0.82,
        "HELD-OUT FORECAST · 2024-2025\n"
        f"Persistence MAE  {metrics['persistence_mae']:.4f}\n"
        f"Delta MAE          {metrics['delta_mae']:.4f}\n"
        f"Difference         {metrics['mae_change_pct']:+.2f}%  · effectively tied",
        transform=top.transAxes,
        ha="left",
        va="top",
        fontsize=11.5,
        color=INK,
        linespacing=1.45,
        bbox={
            "boxstyle": "round,pad=0.65,rounding_size=0.25",
            "facecolor": WHITE,
            "edgecolor": TEAL,
            "linewidth": 1.4,
            "alpha": 0.97,
        },
        zorder=8,
    )
    top.annotate(
        "Final forecast begins",
        xy=(test_start, min(actuals)),
        xytext=(test_start, min(actuals) - 4.8),
        ha="left",
        va="top",
        fontsize=10.5,
        color=TEAL,
        fontweight="bold",
        arrowprops={"arrowstyle": "-|>", "color": TEAL, "linewidth": 1.3},
    )

    by_source: Dict[str, List[Dict[str, object]]] = {source: [] for source in SOURCE_ORDER}
    for row in weight_rows:
        by_source[str(row["source"])].append(row)
    for source in SOURCE_ORDER:
        source_rows = by_source[source]
        bottom.plot(
            [_month(str(row["date"])) for row in source_rows],
            [float(row["signed_weight"]) for row in source_rows],
            color=SOURCE_COLORS[source],
            linewidth=2.5,
            label=SOURCE_LABELS[source],
            zorder=3,
        )

    threshold = threshold_for_budget(STORY_BUDGET_RATIO)
    bottom.axhline(0.0, color=GRAY, linewidth=1.0, zorder=1)
    bottom.axhline(threshold, color=GRAY, linewidth=1.1, linestyle=":", zorder=1)
    bottom.axhline(-threshold, color=GRAY, linewidth=1.1, linestyle=":", zorder=1)
    bottom.text(
        dates[1],
        threshold + 0.035,
        "fixed filter boundary  |weight| > 0.28",
        color=MUTED,
        fontsize=10,
        va="bottom",
    )
    bottom.set_ylim(-1.08, 1.08)
    bottom.set_ylabel("Signed lagged correlation", fontsize=13.5, color=INK)
    bottom.legend(
        loc="lower left",
        frameon=False,
        ncol=4,
        fontsize=11,
        handlelength=2.4,
    )
    bottom.text(
        0.012,
        0.92,
        "WHAT MOVED WITH RETAIL? · PAST-ONLY RELATIONSHIP WEIGHTS",
        transform=bottom.transAxes,
        fontsize=11,
        color=MUTED,
        fontweight="bold",
    )

    retained_lines = [
        f"{SOURCE_LABELS[source]}  {cutoff_weights[source]:+.3f}"
        for source in ("industrial_production", "unemployment_rate")
    ]
    filtered_lines = [
        f"{SOURCE_LABELS[source]}  {cutoff_weights[source]:+.3f}"
        for source in ("consumer_confidence", "hicp")
    ]
    bottom.text(
        0.705,
        0.87,
        "AT THE JAN 2024 CUTOFF\n"
        "RETAINED\n"
        + "\n".join(retained_lines)
        + "\nFILTERED\n"
        + "\n".join(filtered_lines),
        transform=bottom.transAxes,
        ha="left",
        va="top",
        fontsize=10.5,
        color=INK,
        linespacing=1.35,
        bbox={
            "boxstyle": "round,pad=0.55,rounding_size=0.25",
            "facecolor": WHITE,
            "edgecolor": LIGHT_GRAY,
            "linewidth": 1.2,
            "alpha": 0.96,
        },
        zorder=8,
    )

    bottom.xaxis.set_major_locator(mdates.YearLocator())
    bottom.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    bottom.set_xlim(_month(DISPLAY_START), _month(DISPLAY_END))
    bottom.set_xlabel("Month", fontsize=13.5, color=INK)
    plt.setp(top.get_xticklabels(), visible=False)

    figure.suptitle(
        "Spain Retail, 2016-2025: What Moved With It, and What Predicted Next",
        fontsize=22,
        fontweight="bold",
        color=INK,
        y=0.975,
    )
    figure.text(
        0.5,
        0.937,
        "Ten years of real Eurostat data · forecasts only where a held-out prediction exists",
        ha="center",
        va="center",
        fontsize=12.5,
        color=MUTED,
    )
    figure.text(
        0.985,
        0.012,
        "Eurostat Spain · 120-month view · past-only weights · co-movement, not causation",
        ha="right",
        va="bottom",
        fontsize=9.5,
        color=MUTED,
    )
    figure.subplots_adjust(left=0.08, right=0.98, top=0.90, bottom=0.075)
    figure.savefig(
        FIGURE_PATH,
        dpi=180,
        facecolor=WHITE,
        metadata={"Software": "Nestor Delta"},
    )
    figure.savefig(
        SVG_PATH,
        facecolor=WHITE,
        metadata={"Creator": "Nestor Delta", "Date": None},
    )
    plt.close(figure)


def main() -> None:
    config = load_real_case_config(CONFIG_PATH)
    data = load_real_case_data(config)
    forecasts, selected_sources = _load_frozen_forecast()
    metrics = _load_frozen_metrics()

    rolling_weights = _rolling_weights(
        data.dates,
        data.rows,
        data.variables,
        config.target,
        config.lag_window,
    )
    series_rows = _story_series(
        data.dates, data.rows, config.target, forecasts
    )
    cutoff_weights = _validate_cutoff(rolling_weights, selected_sources)

    test_rows = [
        row for row in series_rows if row["delta_prediction"] is not None
    ]
    computed_delta_mae = mae(
        [float(row["actual"]) for row in test_rows],
        [float(row["delta_prediction"]) for row in test_rows],
    )
    if abs(computed_delta_mae - metrics["delta_mae"]) > 1e-9:
        raise ValueError("story forecast does not reproduce frozen Delta MAE")

    _write_series(series_rows)
    _write_weights(rolling_weights)
    _plot(series_rows, rolling_weights, cutoff_weights, metrics)
    print(f"Wrote {SERIES_PATH}")
    print(f"Wrote {WEIGHTS_PATH}")
    print(f"Wrote {FIGURE_PATH}")
    print(f"Wrote {SVG_PATH}")


if __name__ == "__main__":
    main()
