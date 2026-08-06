"""Synthetic time series with a frozen, known Sprint 4 coefficient drift."""

from __future__ import annotations

import csv
import random
from pathlib import Path
from typing import Dict, List

from .config import SERIES_LENGTH
from .s4_config import (
    DRIFT_COEFFICIENT_END,
    DRIFT_COEFFICIENT_START,
    DRIFT_END,
    DRIFT_START,
    DRIFT_TRUTH_COLUMNS,
)
from .synthetic import Row, write_series_csv

TruthRow = Dict[str, float]


def driver_a_coefficient(step: int) -> float:
    """Return the frozen lag-1 driver_a coefficient at one time step."""
    if step < 0:
        raise ValueError("step must be non-negative")
    if step <= DRIFT_START - 1:
        return DRIFT_COEFFICIENT_START
    if step >= DRIFT_END:
        return DRIFT_COEFFICIENT_END
    progress = (step - DRIFT_START) / (DRIFT_END - DRIFT_START)
    return DRIFT_COEFFICIENT_START + (
        DRIFT_COEFFICIENT_END - DRIFT_COEFFICIENT_START
    ) * progress


def generate_drift_series(seed: int, length: int = SERIES_LENGTH) -> List[Row]:
    """Generate one deterministic series from the frozen Sprint 4 protocol."""
    rng = random.Random(seed)
    rows: List[Row] = []

    for step in range(length):
        eps_a = rng.gauss(0.0, 0.80)
        eps_b = rng.gauss(0.0, 0.80)
        eps_noise = rng.gauss(0.0, 1.00)
        eps_target = rng.gauss(0.0, 0.50)

        prev_target = rows[step - 1]["target"] if step - 1 >= 0 else 0.0
        prev_driver_a = rows[step - 1]["driver_a"] if step - 1 >= 0 else 0.0
        prev_driver_b = rows[step - 1]["driver_b"] if step - 1 >= 0 else 0.0
        lag2_driver_b = rows[step - 2]["driver_b"] if step - 2 >= 0 else 0.0

        driver_a = 0.65 * prev_driver_a + eps_a
        driver_b = 0.55 * prev_driver_b + eps_b
        noise = eps_noise
        target = (
            0.55 * prev_target
            + driver_a_coefficient(step) * prev_driver_a
            - 0.25 * lag2_driver_b
            + eps_target
        )

        rows.append(
            {
                "step": float(step),
                "target": target,
                "driver_a": driver_a,
                "driver_b": driver_b,
                "noise": noise,
            }
        )

    return rows


def generate_drift_truth(length: int = SERIES_LENGTH) -> List[TruthRow]:
    """Generate the auditable coefficient truth trajectory."""
    return [
        {
            "step": float(step),
            "coef_driver_a_lag1": driver_a_coefficient(step),
        }
        for step in range(length)
    ]


def write_drift_series_csv(rows: List[Row], path: Path) -> None:
    """Write drift data with the same schema as the original synthetic data."""
    write_series_csv(rows, path)


def write_drift_truth_csv(rows: List[TruthRow], path: Path) -> None:
    """Write the known coefficient path separately from model input data."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=DRIFT_TRUTH_COLUMNS, lineterminator="\n"
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "step": int(row["step"]),
                    "coef_driver_a_lag1": (
                        f"{row['coef_driver_a_lag1']:.10f}"
                    ),
                }
            )
