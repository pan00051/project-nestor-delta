"""Sample-size aware significance thresholds for correlation scores.

Sprint 8 (evaluation power). This module answers one question:

    Given ``n`` paired observations, how large must ``|r|`` be before it is
    distinguishable from luck?

The frozen Sprint 5 constant ``BENCHMARK_NOISE_FLOOR = 0.06`` is a fixed number
that does not depend on ``n``. For the Spain train window (``n = 191``) the
two-sigma threshold is roughly ``0.145``, so ``0.06`` sits *below* the noise
floor and admits relations that cannot be told apart from chance.

This module does not modify Sprint 5 behaviour. It provides the measurement
that a later Evidence Gate can consume.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from statistics import NormalDist


@dataclass(frozen=True)
class NoiseFloor:
    """A correlation threshold and the assumptions that produced it."""

    sample_count: int
    comparisons: int
    alpha: float
    threshold: float

    def clears(self, score: float) -> bool:
        """True when an absolute correlation score exceeds the threshold."""
        return abs(score) > self.threshold


def fisher_z_threshold(sample_count: int, alpha: float = 0.05) -> float:
    """Two-sided ``|r|`` threshold for a single comparison at level ``alpha``.

    Uses the Fisher z transform, whose null standard error is ``1/sqrt(n - 3)``.
    """
    _validate_sample_count(sample_count)
    _validate_alpha(alpha)
    critical = NormalDist().inv_cdf(1.0 - alpha / 2.0)
    return math.tanh(critical / math.sqrt(sample_count - 3))


def sidak_alpha(alpha: float, comparisons: int) -> float:
    """Per-comparison level that holds family-wise error at ``alpha``.

    Delta selects a relation by taking the maximum ``|r|`` over several lags,
    which is a multiple comparison. Without this correction the reported score
    is biased upward by the selection itself.
    """
    _validate_alpha(alpha)
    if comparisons < 1:
        raise ValueError("comparisons must be at least 1")
    return 1.0 - (1.0 - alpha) ** (1.0 / comparisons)


def correlation_noise_floor(
    sample_count: int, comparisons: int = 1, alpha: float = 0.05
) -> NoiseFloor:
    """Threshold for the largest ``|r|`` taken over ``comparisons`` candidates."""
    adjusted = sidak_alpha(alpha, comparisons)
    return NoiseFloor(
        sample_count=sample_count,
        comparisons=comparisons,
        alpha=alpha,
        threshold=fisher_z_threshold(sample_count, adjusted),
    )


def lag_scan_noise_floor(
    sample_count: int, max_lag: int, alpha: float = 0.05
) -> NoiseFloor:
    """Noise floor for the ``argmax`` over ``lag = 1..max_lag`` used by Delta."""
    if max_lag < 1:
        raise ValueError("max_lag must be at least 1")
    return correlation_noise_floor(sample_count, comparisons=max_lag, alpha=alpha)


def _validate_sample_count(sample_count: int) -> None:
    if sample_count <= 3:
        raise ValueError("sample_count must exceed 3 for a Fisher z threshold")


def _validate_alpha(alpha: float) -> None:
    if not 0.0 < alpha < 1.0:
        raise ValueError("alpha must lie strictly between 0 and 1")
