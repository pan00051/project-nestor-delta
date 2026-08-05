"""Metric functions for baseline evaluation."""

from __future__ import annotations

import math
from typing import Sequence


def mae(actual: Sequence[float], predicted: Sequence[float]) -> float:
    if len(actual) != len(predicted):
        raise ValueError("actual and predicted lengths differ")
    return sum(abs(a - p) for a, p in zip(actual, predicted)) / len(actual)


def rmse(actual: Sequence[float], predicted: Sequence[float]) -> float:
    if len(actual) != len(predicted):
        raise ValueError("actual and predicted lengths differ")
    mse = sum((a - p) ** 2 for a, p in zip(actual, predicted)) / len(actual)
    return math.sqrt(mse)
