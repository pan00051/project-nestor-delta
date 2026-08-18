"""Rolling-origin (multi-fold) evaluation splits.

Sprint 8 (evaluation power). The frozen Sprint 0/1 protocol uses one
chronological split with a single test window. On the Spain retail case that
window holds 24 monthly observations, which puts the standard error of the
MAE skill ratio near 20 percent -- larger than any effect later sprints hope
to detect. A single split cannot distinguish a real improvement from sampling
noise.

This module replaces the single origin with many, evaluating the same model
at successive forecast origins so that skill can be reported as a distribution
instead of one number.

Sprint 0/1 splits are untouched and remain the frozen v1 protocol.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Sequence, Tuple


@dataclass(frozen=True)
class RollingOriginFold:
    """One forecast origin: train rows strictly precede test rows."""

    fold_index: int
    train_label_rows: Tuple[int, ...]
    test_label_rows: Tuple[int, ...]

    @property
    def origin(self) -> int:
        """First label row that is forecast in this fold."""
        return self.test_label_rows[0]


def build_rolling_origin_folds(
    label_rows: Sequence[int],
    test_size: int,
    min_train_size: int,
    step: int = 1,
    expanding: bool = True,
    max_folds: int | None = None,
) -> List[RollingOriginFold]:
    """Build past-only folds over an ordered sequence of label rows.

    With ``expanding=True`` each fold trains on every label row before the
    origin (anchored window). With ``expanding=False`` the train window slides
    and keeps a fixed width of ``min_train_size``.

    The construction is deterministic and depends only on its arguments.
    """
    ordered = tuple(label_rows)
    if list(ordered) != sorted(ordered):
        raise ValueError("label_rows must be sorted ascending")
    if len(set(ordered)) != len(ordered):
        raise ValueError("label_rows must be unique")
    if test_size < 1:
        raise ValueError("test_size must be at least 1")
    if min_train_size < 1:
        raise ValueError("min_train_size must be at least 1")
    if step < 1:
        raise ValueError("step must be at least 1")
    if len(ordered) < min_train_size + test_size:
        raise ValueError("not enough label rows for one fold")

    folds: List[RollingOriginFold] = []
    origin_index = min_train_size
    while origin_index + test_size <= len(ordered):
        train_start = 0 if expanding else origin_index - min_train_size
        folds.append(
            RollingOriginFold(
                fold_index=len(folds),
                train_label_rows=ordered[train_start:origin_index],
                test_label_rows=ordered[origin_index : origin_index + test_size],
            )
        )
        if max_folds is not None and len(folds) >= max_folds:
            break
        origin_index += step

    if not folds:
        raise ValueError("no fold could be constructed")
    return folds


def assert_folds_are_past_only(folds: Sequence[RollingOriginFold]) -> None:
    """Raise when any fold trains on a row at or after its own origin."""
    for fold in folds:
        if not fold.train_label_rows:
            raise ValueError(f"fold {fold.fold_index} has an empty train window")
        if not fold.test_label_rows:
            raise ValueError(f"fold {fold.fold_index} has an empty test window")
        if max(fold.train_label_rows) >= fold.origin:
            raise ValueError(
                f"fold {fold.fold_index} trains on row {max(fold.train_label_rows)} "
                f"at or after its origin {fold.origin}"
            )
