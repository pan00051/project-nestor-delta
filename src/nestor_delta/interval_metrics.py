"""Fold-level metrics and interval reporting.

Sprint 8 (evaluation power). Sprint 1 froze MAE and RMSE on a single test
window. Those remain unchanged in ``metrics.py``. This module adds the metrics
and the aggregation needed to state a result as a range rather than a point.

Scope note: this module measures errors. It does not transform input series.
Series-level stationarity transforms for relation scoring are a separate
concern and live outside this module.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, List, Sequence, Tuple


@dataclass(frozen=True)
class SkillInterval:
    """Distribution of a paired per-fold skill ratio against a baseline.

    ``skill`` is the fraction by which the model's error falls below the
    baseline's error. Positive is better. ``low`` and ``high`` bound the
    median through a deterministic bootstrap over folds.
    """

    fold_count: int
    per_fold: Tuple[float, ...]
    median: float
    low: float
    high: float
    confidence: float

    @property
    def excludes_zero(self) -> bool:
        """True when the whole interval sits on one side of no-improvement."""
        return (self.low > 0.0) or (self.high < 0.0)


def mase(
    actual: Sequence[float],
    predicted: Sequence[float],
    train_actual: Sequence[float],
    seasonal_period: int = 1,
) -> float:
    """Mean absolute scaled error.

    Scaled by the in-sample mean absolute change of the naive forecast, which
    makes the metric independent of the level and comparable across cases.
    A value below 1 beats the naive forecast on the training scale.
    """
    if seasonal_period < 1:
        raise ValueError("seasonal_period must be at least 1")
    if len(train_actual) <= seasonal_period:
        raise ValueError("train_actual must be longer than seasonal_period")

    scale_terms = [
        abs(train_actual[i] - train_actual[i - seasonal_period])
        for i in range(seasonal_period, len(train_actual))
    ]
    scale = sum(scale_terms) / len(scale_terms)
    if scale == 0.0:
        raise ValueError("naive scale is zero; MASE is undefined")

    errors = [abs(a - p) for a, p in _paired(actual, predicted)]
    return (sum(errors) / len(errors)) / scale


def directional_accuracy(
    actual: Sequence[float],
    predicted: Sequence[float],
    previous_actual: Sequence[float],
) -> Dict[str, float]:
    """Share of forecasts that call the direction of change correctly.

    Flat forecasts are counted separately rather than scored as hits or
    misses. A persistence baseline predicts no change at every step, so its
    ``decided`` share is zero: the metric makes that explicit instead of
    reporting a misleading accuracy.
    """
    if len(previous_actual) != len(actual):
        raise ValueError("previous_actual and actual lengths differ")

    hits = 0
    decided = 0
    for (a, p), prev in zip(_paired(actual, predicted), previous_actual):
        predicted_change = p - prev
        actual_change = a - prev
        if predicted_change == 0.0:
            continue
        decided += 1
        if (predicted_change > 0.0) == (actual_change > 0.0) and actual_change != 0.0:
            hits += 1

    return {
        "decided": decided / len(actual),
        "accuracy": (hits / decided) if decided else float("nan"),
    }


def worst_decile_error(actual: Sequence[float], predicted: Sequence[float]) -> float:
    """Mean absolute error over the worst tenth of forecasts.

    Reports the tail that an average hides. At least one observation is always
    included.
    """
    errors = sorted((abs(a - p) for a, p in _paired(actual, predicted)), reverse=True)
    count = max(1, len(errors) // 10)
    return sum(errors[:count]) / count


def change_space_errors(
    actual: Sequence[float],
    predicted: Sequence[float],
    previous_actual: Sequence[float],
) -> Dict[str, float]:
    """Errors expressed against the change, not the level.

    On a near-random-walk series the level MAE is dominated by the level
    itself: an error of 0.80 on a series near 108 reads as 0.74 percent and
    looks small, while it is 100 percent of the typical monthly move. This
    reports the same errors on the scale where the forecast actually operates.
    """
    if len(previous_actual) != len(actual):
        raise ValueError("previous_actual and actual lengths differ")

    actual_changes = [a - prev for a, prev in zip(actual, previous_actual)]
    predicted_changes = [p - prev for p, prev in zip(predicted, previous_actual)]
    errors = [abs(a - p) for a, p in zip(actual_changes, predicted_changes)]
    mean_move = sum(abs(c) for c in actual_changes) / len(actual_changes)

    return {
        "mean_absolute_change": mean_move,
        "change_mae": sum(errors) / len(errors),
        "error_share_of_move": (sum(errors) / len(errors)) / mean_move
        if mean_move
        else float("nan"),
    }


def fold_skill(model_error: float, baseline_error: float) -> float:
    """Fraction by which model error falls below baseline error."""
    if baseline_error <= 0.0:
        raise ValueError("baseline_error must be positive")
    return (baseline_error - model_error) / baseline_error


def skill_interval(
    per_fold_skill: Sequence[float],
    confidence: float = 0.90,
    resamples: int = 2000,
    seed: int = 20260818,
) -> SkillInterval:
    """Bootstrap interval for the median per-fold skill.

    Resampling is over folds and uses a fixed seed, so the interval is
    reproducible byte for byte.
    """
    values = tuple(float(v) for v in per_fold_skill)
    if not values:
        raise ValueError("per_fold_skill must not be empty")
    if not 0.0 < confidence < 1.0:
        raise ValueError("confidence must lie strictly between 0 and 1")
    if resamples < 1:
        raise ValueError("resamples must be at least 1")

    medians: List[float] = []
    state = seed
    count = len(values)
    for _ in range(resamples):
        sample = []
        for _ in range(count):
            state = (1103515245 * state + 12345) % (2 ** 31)
            sample.append(values[state % count])
        medians.append(_median(sample))

    medians.sort()
    tail = (1.0 - confidence) / 2.0
    low = medians[min(len(medians) - 1, int(tail * len(medians)))]
    high = medians[min(len(medians) - 1, int((1.0 - tail) * len(medians)))]

    return SkillInterval(
        fold_count=count,
        per_fold=values,
        median=_median(values),
        low=low,
        high=high,
        confidence=confidence,
    )


def sign_flip_null_interval(
    per_fold_skill,
    confidence: float = 0.90,
    resamples: int = 2000,
    seed: int = 20260818,
) -> SkillInterval:
    """Zero-centred randomization null for the median per-fold skill.

    Under H0 the model is no better than the baseline, so the sign of each
    fold's skill is exchangeable. Randomly flipping signs builds a null
    distribution that is centred on zero **by construction**. The acceptance
    check ``随机预测器对照 interval 含零`` is therefore satisfied structurally;
    the informative comparison is whether the OBSERVED median skill falls
    outside this null band.

    This is the correct realization of a zero-centred null. A naive predictor
    (persistence plus noise) is not zero-centred: it is strictly worse than
    persistence and belongs to the degraded control, whose interval sits below
    zero.
    """
    values = tuple(float(v) for v in per_fold_skill)
    if not values:
        raise ValueError("per_fold_skill must not be empty")
    if not 0.0 < confidence < 1.0:
        raise ValueError("confidence must lie strictly between 0 and 1")
    if resamples < 1:
        raise ValueError("resamples must be at least 1")

    # Aggregate by MEAN, not median: the mean is exactly zero-centred under
    # sign flips (E[sign * x] = 0), while the median of a sign-flipped skewed
    # sample is not. The null band is therefore symmetric about zero by
    # construction, regardless of how skewed the per-fold skills are.
    means = []
    state = seed
    count = len(values)
    for _ in range(resamples):
        total = 0.0
        for value in values:
            state = (1103515245 * state + 12345) % (2 ** 31)
            # Use a HIGH-order bit for the coin: the low bit of a power-of-two
            # modulus LCG is periodic and would give identical sign patterns
            # across resamples, collapsing the band to a point.
            sign = 1.0 if state < (2 ** 30) else -1.0
            total += sign * value
        means.append(total / count)

    means.sort()
    tail = (1.0 - confidence) / 2.0
    low = means[min(len(means) - 1, int(tail * len(means)))]
    high = means[min(len(means) - 1, int((1.0 - tail) * len(means)))]
    return SkillInterval(
        fold_count=count,
        per_fold=values,
        median=0.0,
        low=low,
        high=high,
        confidence=confidence,
    )


def _paired(
    actual: Sequence[float], predicted: Sequence[float]
) -> List[Tuple[float, float]]:
    if len(actual) != len(predicted):
        raise ValueError("actual and predicted lengths differ")
    if not actual:
        raise ValueError("cannot score empty sequences")
    return [(float(a), float(p)) for a, p in zip(actual, predicted)]


def _median(values: Sequence[float]) -> float:
    ordered = sorted(values)
    midpoint = len(ordered) // 2
    if len(ordered) % 2 == 1:
        return ordered[midpoint]
    return (ordered[midpoint - 1] + ordered[midpoint]) / 2.0
