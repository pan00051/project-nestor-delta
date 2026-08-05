"""Synthetic multivariate time-series generation for Sprint 1."""

from __future__ import annotations

import csv
import random
from pathlib import Path
from typing import Dict, List

from .config import CSV_COLUMNS, SERIES_LENGTH

Row = Dict[str, float]


def generate_series(seed: int, length: int = SERIES_LENGTH) -> List[Row]:
    """Generate one deterministic synthetic series from the frozen protocol."""
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
            + 0.35 * prev_driver_a
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


def write_series_csv(rows: List[Row], path: Path) -> None:
    """Write generated rows with stable column order and precision."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "step": int(row["step"]),
                    "target": f"{row['target']:.10f}",
                    "driver_a": f"{row['driver_a']:.10f}",
                    "driver_b": f"{row['driver_b']:.10f}",
                    "noise": f"{row['noise']:.10f}",
                }
            )
