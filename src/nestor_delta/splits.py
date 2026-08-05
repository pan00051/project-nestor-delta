"""Chronological split helpers for the frozen Sprint 1 protocol."""

from __future__ import annotations

from typing import Iterable, List, Sequence, Tuple

from .config import FEATURE_COLUMNS, LAG_WINDOW
from .synthetic import Row

Features = List[float]


def build_lagged_samples(
    rows: Sequence[Row], label_rows: Iterable[int], lag_window: int = LAG_WINDOW
) -> Tuple[List[Features], List[float]]:
    """Build supervised samples whose features never use rows after label - 1."""
    features: List[Features] = []
    labels: List[float] = []

    for label_index in label_rows:
        sample: Features = [1.0]
        for lag in range(1, lag_window + 1):
            source = rows[label_index - lag]
            sample.extend(float(source[column]) for column in FEATURE_COLUMNS)

        features.append(sample)
        labels.append(float(rows[label_index]["target"]))

    return features, labels
