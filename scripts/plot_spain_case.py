#!/usr/bin/env python3
"""Render presentation charts for the frozen Eurostat Spain retail case."""

from __future__ import annotations

import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter, MaxNLocator


ROOT = Path(__file__).resolve().parents[1]
CASE_NAME = "spain_retail_eurostat_2008_2025"
REPORT_DIR = ROOT / "reports" / CASE_NAME
METRICS_PATH = REPORT_DIR / "real_budget_sweep_metrics.csv"
CASE_DATA_PATH = ROOT / "cases" / CASE_NAME / "data.csv"

TRADEOFF_PATH = REPORT_DIR / "budget_accuracy_tradeoff.png"
RETENTION_PATH = REPORT_DIR / "signal_retention.png"

NAVY = "#123B5D"
TEAL = "#007C83"
CORAL = "#D94F3D"
INK = "#17212B"
MUTED = "#64727F"
LIGHT = "#D9E1E7"
WHITE = "#FFFFFF"


def _load_metrics() -> list[dict[str, object]]:
    required = {
        "budget_ratio",
        "mae_change_vs_persistence_pct",
        "actual_ols_signal_count",
        "actual_ols_sources",
    }
    with METRICS_PATH.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None or not required.issubset(reader.fieldnames):
            missing = sorted(required.difference(reader.fieldnames or []))
            raise ValueError(f"Missing required metrics columns: {', '.join(missing)}")

        rows: list[dict[str, object]] = []
        for raw in reader:
            rows.append(
                {
                    "budget_ratio": float(raw["budget_ratio"]),
                    "mae_change_vs_persistence_pct": float(
                        raw["mae_change_vs_persistence_pct"]
                    ),
                    "actual_ols_signal_count": int(raw["actual_ols_signal_count"]),
                    "actual_ols_sources": tuple(
                        source
                        for source in raw["actual_ols_sources"].split(";")
                        if source
                    ),
                }
            )

    if not rows:
        raise ValueError("Metrics report contains no rows")
    return sorted(rows, key=lambda row: row["budget_ratio"], reverse=True)


def _count_case_months() -> int:
    with CASE_DATA_PATH.open(newline="", encoding="utf-8") as handle:
        return sum(1 for _ in csv.DictReader(handle))


def _style_axes(ax: plt.Axes) -> None:
    ax.set_facecolor(WHITE)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color(MUTED)
    ax.spines["bottom"].set_color(MUTED)
    ax.tick_params(axis="both", colors=INK, labelsize=13, width=1.2, length=5)
    ax.set_axisbelow(True)


def _format_source(source: str) -> str:
    return source.replace("_", " ")


def _footer(fig: plt.Figure, month_count: int) -> None:
    fig.text(
        0.985,
        0.018,
        f"Eurostat Spain · {month_count} months · reproducible",
        ha="right",
        va="bottom",
        fontsize=9.5,
        color=MUTED,
    )


def _plot_budget_accuracy(
    rows: list[dict[str, object]], month_count: int
) -> None:
    budgets = [float(row["budget_ratio"]) for row in rows]
    mae_changes = [
        float(row["mae_change_vs_persistence_pct"]) for row in rows
    ]
    signal_counts = [int(row["actual_ols_signal_count"]) for row in rows]

    fig, ax = plt.subplots(figsize=(12.8, 7.6), dpi=180)
    fig.patch.set_facecolor(WHITE)
    _style_axes(ax)

    ax.plot(
        budgets,
        mae_changes,
        color=NAVY,
        linewidth=4,
        marker="o",
        markersize=10,
        markerfacecolor=CORAL,
        markeredgecolor=WHITE,
        markeredgewidth=2,
        zorder=3,
    )
    ax.axhline(0, color=TEAL, linewidth=2.2, linestyle="--", zorder=1)
    ax.text(
        0.02,
        0,
        "persistence baseline",
        transform=ax.get_yaxis_transform(),
        ha="left",
        va="bottom",
        fontsize=12,
        color=TEAL,
        fontweight="bold",
    )

    high_count = max(signal_counts)
    low_count = min(signal_counts)
    high_indices = [
        index for index, count in enumerate(signal_counts) if count == high_count
    ]
    low_indices = [
        index for index, count in enumerate(signal_counts) if count == low_count
    ]
    high_mean = sum(mae_changes[index] for index in high_indices) / len(high_indices)

    ax.annotate(
        f"{high_count} signals — overfit (+{high_mean:.0f}%)",
        xy=(budgets[high_indices[-1]], mae_changes[high_indices[-1]]),
        xytext=(0.87, high_mean + 8),
        ha="center",
        va="bottom",
        fontsize=14,
        fontweight="bold",
        color=CORAL,
        arrowprops={"arrowstyle": "-", "color": CORAL, "linewidth": 1.8},
    )
    middle_low = low_indices[len(low_indices) // 2]
    ax.annotate(
        f"{low_count} signals — level with baseline",
        xy=(budgets[middle_low], mae_changes[middle_low]),
        xytext=(0.26, 11),
        ha="center",
        va="bottom",
        fontsize=14,
        fontweight="bold",
        color=TEAL,
        arrowprops={"arrowstyle": "-", "color": TEAL, "linewidth": 1.8},
    )

    for budget, value in zip(budgets, mae_changes):
        offset = 2.7 if value > 1 else -4.7
        ax.text(
            budget,
            value + offset,
            f"{value:+.2f}%",
            ha="center",
            va="center",
            fontsize=12,
            color=INK,
            fontweight="bold",
        )

    ax.set_xlim(1.06, -0.06)
    ax.set_ylim(-10, 82)
    ax.set_xticks(budgets, [f"{budget:.2f}" for budget in budgets])
    ax.set_xlabel("Budget ratio (lower means higher pressure)", fontsize=15, color=INK)
    ax.set_ylabel("MAE change vs persistence (%)", fontsize=15, color=INK)
    ax.set_title(
        "Budget–Accuracy Trade-off: Spain Retail (Eurostat, 2008–2025)",
        fontsize=20,
        fontweight="bold",
        color=INK,
        pad=20,
    )

    _footer(fig, month_count)
    fig.subplots_adjust(left=0.11, right=0.975, top=0.86, bottom=0.15)
    fig.savefig(TRADEOFF_PATH, dpi=180, facecolor=WHITE, metadata={"Software": "Nestor Delta"})
    plt.close(fig)


def _plot_signal_retention(
    rows: list[dict[str, object]], month_count: int
) -> None:
    budgets = [float(row["budget_ratio"]) for row in rows]
    counts = [int(row["actual_ols_signal_count"]) for row in rows]
    sources = [tuple(row["actual_ols_sources"]) for row in rows]

    fig, ax = plt.subplots(figsize=(12.8, 7.6), dpi=180)
    fig.patch.set_facecolor(WHITE)
    _style_axes(ax)

    ax.step(
        budgets,
        counts,
        where="mid",
        color=TEAL,
        linewidth=4,
        zorder=2,
    )
    ax.plot(
        budgets,
        counts,
        linestyle="none",
        marker="o",
        markersize=11,
        markerfacecolor=CORAL,
        markeredgecolor=WHITE,
        markeredgewidth=2,
        zorder=3,
    )

    for budget, count in zip(budgets, counts):
        ax.text(
            budget,
            count + 0.16,
            str(count),
            ha="center",
            va="bottom",
            fontsize=14,
            color=INK,
            fontweight="bold",
        )

    source_groups: list[tuple[int, tuple[str, ...], list[int]]] = []
    for index, (count, row_sources) in enumerate(zip(counts, sources)):
        if source_groups and source_groups[-1][1] == row_sources:
            source_groups[-1][2].append(index)
        else:
            source_groups.append((count, row_sources, [index]))

    for group_index, (count, row_sources, indices) in enumerate(source_groups):
        center_budget = sum(budgets[index] for index in indices) / len(indices)
        display_sources = [_format_source(source) for source in row_sources]
        if group_index == 0:
            label = (
                f"All {count} signals\n"
                + " · ".join(display_sources[:2])
                + "\n"
                + " · ".join(display_sources[2:])
            )
            label_y = count + 0.72
        else:
            label = f"Retained {count}\n" + " + ".join(display_sources)
            label_y = count + 0.72
        ax.text(
            center_budget,
            label_y,
            label,
            ha="center",
            va="bottom",
            fontsize=11.8,
            color=NAVY,
            fontweight="bold",
            linespacing=1.35,
        )

    ax.set_xlim(1.06, -0.06)
    ax.set_ylim(0.7, 5.75)
    ax.set_xticks(budgets, [f"{budget:.2f}" for budget in budgets])
    ax.yaxis.set_major_locator(MaxNLocator(integer=True))
    ax.yaxis.set_major_formatter(FuncFormatter(lambda value, _: f"{int(value)}"))
    ax.set_xlabel("Budget ratio (lower means higher pressure)", fontsize=15, color=INK)
    ax.set_ylabel("Signals entering OLS", fontsize=15, color=INK)
    ax.set_title(
        "Signals Retained Under Rising Budget Pressure",
        fontsize=20,
        fontweight="bold",
        color=INK,
        pad=20,
    )

    _footer(fig, month_count)
    fig.subplots_adjust(left=0.10, right=0.975, top=0.86, bottom=0.15)
    fig.savefig(RETENTION_PATH, dpi=180, facecolor=WHITE, metadata={"Software": "Nestor Delta"})
    plt.close(fig)


def main() -> None:
    rows = _load_metrics()
    month_count = _count_case_months()
    _plot_budget_accuracy(rows, month_count)
    _plot_signal_retention(rows, month_count)
    print(f"Wrote {TRADEOFF_PATH}")
    print(f"Wrote {RETENTION_PATH}")


if __name__ == "__main__":
    main()
