"""Frozen high-dimensional fixture for Sprint 5 resource stress tests."""

from __future__ import annotations

import csv
import random
from pathlib import Path
from typing import Dict, List

from .s5_config import (
    RESOURCE_STRESS_COLUMNS,
    RESOURCE_STRESS_CSV_COLUMNS,
    RESOURCE_STRESS_LENGTH,
    RESOURCE_STRESS_MEDIUM_SOURCES,
    RESOURCE_STRESS_NOISE_SOURCES,
    RESOURCE_STRESS_SOURCES,
    RESOURCE_STRESS_STRONG_SOURCES,
    RESOURCE_STRESS_TARGET,
    RESOURCE_STRESS_WEAK_SOURCES,
)
from .synthetic import Row

RESOURCE_STRESS_EFFECTS = {
    "strong_1": 0.75,
    "strong_2": -0.65,
    "strong_3": 0.55,
    "medium_1": 0.48,
    "medium_2": -0.42,
    "medium_3": 0.36,
    "medium_4": -0.30,
    "weak_1": 0.25,
    "weak_2": -0.20,
    "weak_3": 0.15,
    "weak_4": -0.10,
}


def generate_resource_stress_series(
    seed: int, length: int = RESOURCE_STRESS_LENGTH
) -> List[Row]:
    """Generate a deterministic relation-strength ladder fixture."""
    rng = random.Random(seed)
    rows: List[Row] = []
    previous = {column: 0.0 for column in RESOURCE_STRESS_COLUMNS}

    for step in range(length):
        current: Dict[str, float] = {"step": float(step)}
        for index, source in enumerate(RESOURCE_STRESS_SOURCES):
            ar_strength = 0.20 + 0.03 * (index % 4)
            current[source] = (
                ar_strength * previous[source] + rng.gauss(0.0, 1.0)
            )

        target = 0.30 * previous[RESOURCE_STRESS_TARGET]
        for source, coefficient in RESOURCE_STRESS_EFFECTS.items():
            target += coefficient * previous[source]
        target += rng.gauss(0.0, 0.45)
        current[RESOURCE_STRESS_TARGET] = target
        rows.append(current)
        previous = {
            column: float(current[column])
            for column in RESOURCE_STRESS_COLUMNS
        }

    return rows


def source_tier(source: str) -> str:
    if source in RESOURCE_STRESS_STRONG_SOURCES:
        return "strong"
    if source in RESOURCE_STRESS_MEDIUM_SOURCES:
        return "medium"
    if source in RESOURCE_STRESS_WEAK_SOURCES:
        return "weak"
    if source in RESOURCE_STRESS_NOISE_SOURCES:
        return "noise"
    raise ValueError(f"unknown resource stress source: {source!r}")


def write_resource_stress_csv(rows: List[Row], path: Path) -> None:
    """Write the stress fixture with stable column order and precision."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=RESOURCE_STRESS_CSV_COLUMNS, lineterminator="\n"
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "step": int(row["step"]),
                    **{
                        column: f"{float(row[column]):.10f}"
                        for column in RESOURCE_STRESS_COLUMNS
                    },
                }
            )
