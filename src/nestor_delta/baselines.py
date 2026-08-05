"""Frozen Sprint 1 baseline implementations."""

from __future__ import annotations

from typing import Iterable, List, Sequence

from .synthetic import Row


def predict_persistence(rows: Sequence[Row], label_rows: Iterable[int]) -> List[float]:
    """Predict target at label row i with target at row i - 1."""
    return [float(rows[label_index - 1]["target"]) for label_index in label_rows]


def fit_linear_regression(features: Sequence[Sequence[float]], labels: Sequence[float]) -> List[float]:
    """Fit deterministic OLS via normal equations and Gaussian elimination."""
    if not features:
        raise ValueError("features must not be empty")

    feature_count = len(features[0])
    xtx = [[0.0 for _ in range(feature_count)] for _ in range(feature_count)]
    xty = [0.0 for _ in range(feature_count)]

    for row, label in zip(features, labels):
        if len(row) != feature_count:
            raise ValueError("all feature rows must have the same length")
        for i in range(feature_count):
            xty[i] += row[i] * label
            for j in range(feature_count):
                xtx[i][j] += row[i] * row[j]

    return _solve_linear_system(xtx, xty)


def predict_linear_regression(features: Sequence[Sequence[float]], coefficients: Sequence[float]) -> List[float]:
    return [sum(value * coef for value, coef in zip(row, coefficients)) for row in features]


def _solve_linear_system(matrix: Sequence[Sequence[float]], vector: Sequence[float]) -> List[float]:
    size = len(vector)
    augmented = [list(matrix[row]) + [vector[row]] for row in range(size)]

    for pivot_col in range(size):
        pivot_row = max(range(pivot_col, size), key=lambda row: abs(augmented[row][pivot_col]))
        pivot_value = augmented[pivot_row][pivot_col]
        if abs(pivot_value) < 1e-12:
            raise ValueError("linear system is singular or ill-conditioned")

        if pivot_row != pivot_col:
            augmented[pivot_col], augmented[pivot_row] = augmented[pivot_row], augmented[pivot_col]

        pivot_value = augmented[pivot_col][pivot_col]
        for col in range(pivot_col, size + 1):
            augmented[pivot_col][col] /= pivot_value

        for row in range(size):
            if row == pivot_col:
                continue
            factor = augmented[row][pivot_col]
            if factor == 0.0:
                continue
            for col in range(pivot_col, size + 1):
                augmented[row][col] -= factor * augmented[pivot_col][col]

    return [augmented[row][size] for row in range(size)]
