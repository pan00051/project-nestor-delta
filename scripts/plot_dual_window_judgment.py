#!/usr/bin/env python3
"""Render the frozen dual-window story from committed CSV reports."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter


ROOT = Path(__file__).resolve().parents[1]
REPORT_ROOT = ROOT / "reports"
OUTPUT_PNG = REPORT_ROOT / "dual_window_judgment.png"
OUTPUT_SVG = REPORT_ROOT / "dual_window_judgment.svg"

NAVY = "#123B5D"
TEAL = "#008A8C"
GREEN = "#168A5B"
CORAL = "#D9533F"
AMBER = "#D98900"
INK = "#17212B"
MUTED = "#667687"
GRID = "#DCE4EA"
PALE_BLUE = "#F4F8FB"
PALE_TEAL = "#EDF8F7"
WHITE = "#FFFFFF"


@dataclass(frozen=True)
class PredictionPoint:
    date: datetime
    actual: float
    persistence: float
    delta: float | None


@dataclass(frozen=True)
class CaseOutcome:
    validation_change_pct: float
    test_change_pct: float | None
    final_mode: str
    fit_status: str
    persistence_mae: float
    delta_mae: float | None
    predictions: tuple[PredictionPoint, ...]


def _parse_month(value: str) -> datetime:
    return datetime.strptime(value, "%Y-%m")


def _read_best_validation_change(path: Path) -> float:
    required = {
        "validation_mae",
        "actual_ols_signal_count",
        "relation_threshold",
        "lag_window",
        "max_selected_signals",
        "actual_ols_sources",
        "mae_change_vs_persistence_pct",
    }
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None or not required.issubset(reader.fieldnames):
            missing = sorted(required.difference(reader.fieldnames or []))
            raise ValueError(f"Missing validation columns: {', '.join(missing)}")
        rows = list(reader)
    if not rows:
        raise ValueError(f"No validation rows in {path}")

    def selection_key(row: dict[str, str]) -> tuple[object, ...]:
        sources = tuple(source for source in row["actual_ols_sources"].split(";") if source)
        return (
            float(row["validation_mae"]),
            int(row["actual_ols_signal_count"]),
            -float(row["relation_threshold"]),
            int(row["lag_window"]),
            int(row["max_selected_signals"]),
            sources,
        )

    selected = min(rows, key=selection_key)
    return float(selected["mae_change_vs_persistence_pct"])


def _read_test_metrics(path: Path) -> tuple[str, str, float, float | None, float | None]:
    required = {
        "final_mode",
        "fit_status",
        "persistence_mae",
        "delta_mae",
        "mae_change_vs_persistence_pct",
    }
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None or not required.issubset(reader.fieldnames):
            missing = sorted(required.difference(reader.fieldnames or []))
            raise ValueError(f"Missing test columns: {', '.join(missing)}")
        rows = list(reader)
    if len(rows) != 1:
        raise ValueError(f"Expected one frozen test row in {path}")
    row = rows[0]
    raw_delta_mae = row["delta_mae"].strip()
    raw_change = row["mae_change_vs_persistence_pct"].strip()
    return (
        row["final_mode"],
        row["fit_status"],
        float(row["persistence_mae"]),
        float(raw_delta_mae) if raw_delta_mae else None,
        float(raw_change) if raw_change else None,
    )


def _read_predictions(path: Path) -> tuple[PredictionPoint, ...]:
    required = {"date", "actual", "persistence", "delta_prediction"}
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None or not required.issubset(reader.fieldnames):
            missing = sorted(required.difference(reader.fieldnames or []))
            raise ValueError(f"Missing prediction columns: {', '.join(missing)}")
        rows = tuple(
            PredictionPoint(
                date=_parse_month(row["date"]),
                actual=float(row["actual"]),
                persistence=float(row["persistence"]),
                delta=(
                    float(row["delta_prediction"])
                    if row["delta_prediction"].strip()
                    else None
                ),
            )
            for row in reader
        )
    if not rows:
        raise ValueError(f"No predictions in {path}")
    return rows


def _load_case(case_name: str) -> CaseOutcome:
    case_dir = REPORT_ROOT / case_name
    final_mode, fit_status, persistence_mae, delta_mae, test_change = (
        _read_test_metrics(case_dir / "frozen_test_metrics.csv")
    )
    return CaseOutcome(
        validation_change_pct=_read_best_validation_change(
            case_dir / "validation_parameter_grid.csv"
        ),
        test_change_pct=test_change,
        final_mode=final_mode,
        fit_status=fit_status,
        persistence_mae=persistence_mae,
        delta_mae=delta_mae,
        predictions=_read_predictions(case_dir / "frozen_test_predictions.csv"),
    )


def _signed(value: float) -> str:
    return f"{value:+.2f}%"


def _base_axes(ax: plt.Axes) -> None:
    ax.set_facecolor(WHITE)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color(MUTED)
    ax.spines["bottom"].set_color(MUTED)
    ax.tick_params(axis="both", colors=INK, labelsize=11.5, width=1.1, length=4)
    ax.grid(axis="y", color=GRID, linewidth=0.8, alpha=0.8)
    ax.set_axisbelow(True)


def _shade_windows(ax: plt.Axes) -> None:
    ax.axvspan(_parse_month("2016-01"), _parse_month("2019-12"), color=PALE_BLUE, zorder=0)
    ax.axvspan(_parse_month("2020-01"), _parse_month("2021-12"), color=PALE_TEAL, zorder=0)
    ax.axvline(
        _parse_month("2020-01"),
        color=TEAL,
        linewidth=1.8,
        linestyle=(0, (2, 2)),
        zorder=1,
    )


def _draw_main_panel(ax: plt.Axes, case_a: CaseOutcome, case_b: CaseOutcome) -> None:
    points = case_a.predictions + case_b.predictions
    dates = [point.date for point in points]
    actual = [point.actual for point in points]
    persistence = [point.persistence for point in points]
    delta_dates = [point.date for point in case_b.predictions if point.delta is not None]
    delta_values = [point.delta for point in case_b.predictions if point.delta is not None]

    _base_axes(ax)
    _shade_windows(ax)
    ax.plot(dates, actual, color=NAVY, linewidth=3.1, label="Actual industrial production", zorder=4)
    ax.plot(
        dates,
        persistence,
        color="#8B9AAA",
        linewidth=2.0,
        linestyle="--",
        label="Persistence: previous month",
        zorder=2,
    )
    ax.plot(
        delta_dates,
        delta_values,
        color=TEAL,
        linewidth=3.0,
        marker="o",
        markersize=3.5,
        markevery=3,
        label="Delta forecast: Case B only",
        zorder=3,
    )

    ax.text(
        0.012,
        0.91,
        "WHAT HAPPENED? · HELD-OUT TEST WINDOWS",
        transform=ax.transAxes,
        ha="left",
        va="top",
        color=MUTED,
        fontsize=11,
        fontweight="bold",
    )
    ax.text(
        _parse_month("2017-09"),
        74.2,
        "CASE A · NORMAL PERIOD\n2016–2019",
        ha="center",
        va="bottom",
        color=NAVY,
        fontsize=12.5,
        fontweight="bold",
    )
    ax.text(
        _parse_month("2021-01"),
        74.2,
        "CASE B · SHOCK PERIOD\n2020–2021",
        ha="center",
        va="bottom",
        color=NAVY,
        fontsize=12.5,
        fontweight="bold",
    )

    case_a_box = (
        "VALIDATION GUARD\n"
        f"Best Delta candidate  {_signed(case_a.validation_change_pct)}\n"
        f"Persistence test MAE  {case_a.persistence_mae:.4f}\n"
        "Delta test MAE          —\n"
        "Decision                 baseline-only"
    )
    ax.text(
        _parse_month("2016-04"),
        106.8,
        case_a_box,
        ha="left",
        va="top",
        color=INK,
        fontsize=10.8,
        linespacing=1.35,
        bbox={
            "boxstyle": "round,pad=0.55",
            "facecolor": WHITE,
            "edgecolor": NAVY,
            "linewidth": 1.4,
            "alpha": 0.96,
        },
        zorder=6,
    )

    if case_b.delta_mae is None or case_b.test_change_pct is None:
        raise ValueError("Case B must contain frozen Delta test metrics")
    case_b_box = (
        "ONE-SHOT SHOCK TEST\n"
        f"Validation difference  {_signed(case_b.validation_change_pct)}\n"
        f"Persistence test MAE   {case_b.persistence_mae:.4f}\n"
        f"Delta test MAE          {case_b.delta_mae:.4f}\n"
        f"Test difference         {_signed(case_b.test_change_pct)}"
    )
    ax.text(
        _parse_month("2020-10"),
        106.8,
        case_b_box,
        ha="left",
        va="top",
        color=INK,
        fontsize=10.8,
        linespacing=1.35,
        bbox={
            "boxstyle": "round,pad=0.55",
            "facecolor": WHITE,
            "edgecolor": CORAL,
            "linewidth": 1.4,
            "alpha": 0.96,
        },
        zorder=6,
    )

    ax.annotate(
        "Case B forecast begins",
        xy=(_parse_month("2020-01"), 68.8),
        xytext=(_parse_month("2020-06"), 65.8),
        ha="left",
        va="bottom",
        color=TEAL,
        fontsize=11,
        fontweight="bold",
        arrowprops={"arrowstyle": "-|>", "color": TEAL, "linewidth": 1.5},
    )

    ax.set_ylim(64.5, 112.5)
    ax.set_ylabel("Industrial production index", fontsize=13, color=INK)
    ax.legend(
        loc="upper left",
        bbox_to_anchor=(0.0, 1.025),
        frameon=False,
        ncol=3,
        fontsize=11,
        handlelength=2.7,
        columnspacing=1.8,
    )
    ax.tick_params(axis="x", labelbottom=False)


def _draw_decision_panel(ax: plt.Axes, case_a: CaseOutcome, case_b: CaseOutcome) -> None:
    _base_axes(ax)
    _shade_windows(ax)
    ax.axhline(0, color=MUTED, linewidth=1.2, zorder=1)

    a_cutoff = _parse_month("2016-01")
    a_end = _parse_month("2019-12")
    b_cutoff = _parse_month("2020-01")
    b_end = _parse_month("2021-12")

    ax.scatter(
        [a_cutoff],
        [case_a.validation_change_pct],
        s=115,
        color=CORAL,
        edgecolor=WHITE,
        linewidth=2,
        zorder=4,
    )
    ax.plot(
        [a_cutoff, a_cutoff],
        [case_a.validation_change_pct, 0],
        color=NAVY,
        linestyle=(0, (3, 3)),
        linewidth=2,
        zorder=2,
    )
    ax.plot(
        [a_cutoff, a_end],
        [0, 0],
        color=NAVY,
        linewidth=4,
        solid_capstyle="round",
        zorder=3,
    )
    ax.scatter(
        [a_cutoff],
        [0],
        s=135,
        marker="D",
        color=NAVY,
        edgecolor=WHITE,
        linewidth=2,
        zorder=4,
    )
    ax.text(
        _parse_month("2016-02"),
        4.4,
        f"At the 2016 cutoff: validation {_signed(case_a.validation_change_pct)}\n"
        "Guard triggered · no Delta forecast",
        ha="left",
        va="top",
        color=NAVY,
        fontsize=11,
        fontweight="bold",
        linespacing=1.3,
    )

    if case_b.test_change_pct is None:
        raise ValueError("Case B must contain a frozen test comparison")
    ax.annotate(
        "",
        xy=(b_end, case_b.test_change_pct),
        xytext=(b_cutoff, case_b.validation_change_pct),
        arrowprops={
            "arrowstyle": "-|>",
            "color": NAVY,
            "linewidth": 3.2,
            "mutation_scale": 15,
        },
        zorder=2,
    )
    ax.scatter(
        [b_cutoff],
        [case_b.validation_change_pct],
        s=125,
        color=GREEN,
        edgecolor=WHITE,
        linewidth=2,
        zorder=4,
    )
    ax.scatter(
        [b_end],
        [case_b.test_change_pct],
        s=125,
        color=CORAL,
        edgecolor=WHITE,
        linewidth=2,
        zorder=4,
    )
    ax.text(
        _parse_month("2020-01"),
        case_b.validation_change_pct - 1.0,
        f"Validation {_signed(case_b.validation_change_pct)}\nGate passed",
        ha="center",
        va="top",
        color=GREEN,
        fontsize=11,
        fontweight="bold",
        linespacing=1.25,
    )
    ax.text(
        _parse_month("2021-11"),
        case_b.test_change_pct + 1.0,
        f"Test {_signed(case_b.test_change_pct)}\nPattern reversed",
        ha="right",
        va="bottom",
        color=CORAL,
        fontsize=11,
        fontweight="bold",
        linespacing=1.25,
    )

    ax.text(
        0.012,
        0.95,
        "WHAT DID THE SYSTEM DECIDE? · VALIDATION FROZEN BEFORE TEST",
        transform=ax.transAxes,
        ha="left",
        va="top",
        color=MUTED,
        fontsize=11,
        fontweight="bold",
    )
    ax.text(
        _parse_month("2018-02"),
        0.55,
        "BASELINE-ONLY",
        ha="center",
        va="bottom",
        color=NAVY,
        fontsize=10.5,
        fontweight="bold",
    )

    ax.set_ylim(-11.5, 12.8)
    ax.set_ylabel("MAE change vs persistence", fontsize=13, color=INK)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda value, _: f"{value:+.0f}%"))
    year_ticks = [_parse_month(f"{year}-01") for year in range(2016, 2022)]
    ax.set_xticks(year_ticks, [str(year) for year in range(2016, 2022)])
    ax.set_xlabel("Month", fontsize=13, color=INK)


def _render(case_a: CaseOutcome, case_b: CaseOutcome) -> None:
    if case_a.final_mode != "baseline_only" or case_a.delta_mae is not None:
        raise ValueError("Case A must remain baseline-only with no Delta test metric")
    if any(point.delta is not None for point in case_a.predictions):
        raise ValueError("Case A must not contain emitted Delta test predictions")
    if case_b.final_mode != "delta":
        raise ValueError("Case B must remain the frozen Delta test")

    matplotlib.rcParams["svg.hashsalt"] = "nestor-delta-dual-window"
    fig, (main_ax, decision_ax) = plt.subplots(
        2,
        1,
        figsize=(14.4, 10.2),
        dpi=180,
        sharex=True,
        gridspec_kw={"height_ratios": [1.35, 0.72], "hspace": 0.21},
    )
    fig.patch.set_facecolor(WHITE)

    _draw_main_panel(main_ax, case_a, case_b)
    _draw_decision_panel(decision_ax, case_a, case_b)

    main_ax.set_xlim(_parse_month("2015-11"), _parse_month("2022-02"))
    fig.suptitle(
        "Spain Industrial Production, 2016–2021: Predict, Retreat, Reveal",
        x=0.5,
        y=0.982,
        ha="center",
        color=INK,
        fontsize=22,
        fontweight="bold",
    )
    fig.text(
        0.5,
        0.938,
        "Two held-out windows · parameters chosen on validation · each test evaluated once",
        ha="center",
        color=MUTED,
        fontsize=12.5,
    )
    fig.text(
        0.985,
        0.017,
        "Eurostat Spain · 72 test months · reproducible · co-movement, not causation",
        ha="right",
        color=MUTED,
        fontsize=9.8,
    )

    fig.subplots_adjust(left=0.085, right=0.985, top=0.87, bottom=0.09)
    fig.savefig(
        OUTPUT_PNG,
        dpi=180,
        facecolor=WHITE,
        metadata={"Software": "Nestor Delta"},
    )
    fig.savefig(
        OUTPUT_SVG,
        facecolor=WHITE,
        metadata={"Creator": "Nestor Delta", "Date": None},
    )
    plt.close(fig)


def main() -> None:
    case_a = _load_case("spain_industrial_normal_2008_2021")
    case_b = _load_case("spain_industrial_shock_2008_2021")
    _render(case_a, case_b)
    print(OUTPUT_PNG)
    print(OUTPUT_SVG)


if __name__ == "__main__":
    main()
