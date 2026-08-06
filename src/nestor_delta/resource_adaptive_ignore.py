"""Layer-independent resource-adaptive ignore thresholds."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence, Tuple

from .relation_weights import RelationWeight, rank_target_sources
from .s5_config import (
    BENCHMARK_NOISE_FLOOR,
    BYTES_PER_VALUE,
    MAX_PRESSURE_THRESHOLD,
)


@dataclass(frozen=True)
class ResourceAdaptiveIgnoreConfig:
    """Deterministic threshold bounds for downstream budget adaptation."""

    min_threshold: float = BENCHMARK_NOISE_FLOOR
    max_threshold: float = MAX_PRESSURE_THRESHOLD
    bytes_per_value: int = BYTES_PER_VALUE

    def __post_init__(self) -> None:
        if not 0.0 <= self.min_threshold < self.max_threshold <= 1.0:
            raise ValueError("thresholds must satisfy 0 <= min < max <= 1")
        if self.bytes_per_value <= 0:
            raise ValueError("bytes_per_value must be positive")


@dataclass(frozen=True)
class DownstreamResourceProfile:
    """Estimated downstream work after weak relations are ignored."""

    budget_ratio: float
    threshold: float
    retained_relation_count: int
    retained_feature_count: int
    downstream_lag_count: int
    materialized_lag_count: int
    effective_row_count: int
    downstream_compute_proxy: int
    downstream_memory_proxy: int
    estimated_memory_bytes: int


DEFAULT_IGNORE_CONFIG = ResourceAdaptiveIgnoreConfig()


def threshold_for_budget(
    budget_ratio: float,
    config: ResourceAdaptiveIgnoreConfig = DEFAULT_IGNORE_CONFIG,
) -> float:
    """Map lower downstream budget to a higher ignore threshold."""
    if not 0.0 <= budget_ratio <= 1.0:
        raise ValueError("budget_ratio must be between 0 and 1")
    return config.min_threshold + (1.0 - budget_ratio) * (
        config.max_threshold - config.min_threshold
    )


def retain_relations(
    weights: Sequence[RelationWeight],
    target: str,
    budget_ratio: float,
    config: ResourceAdaptiveIgnoreConfig = DEFAULT_IGNORE_CONFIG,
) -> Tuple[RelationWeight, ...]:
    """Keep target relations whose scores clear the adaptive threshold."""
    threshold = threshold_for_budget(budget_ratio, config)
    return tuple(
        weight
        for weight in rank_target_sources(weights, target)
        if weight.score > threshold
    )


def downstream_profile(
    budget_ratio: float,
    retained_relation_count: int,
    downstream_lag_count: int,
    materialized_lag_count: int,
    effective_row_count: int,
    config: ResourceAdaptiveIgnoreConfig = DEFAULT_IGNORE_CONFIG,
) -> DownstreamResourceProfile:
    """Estimate downstream compute and materialized feature memory."""
    if retained_relation_count < 0:
        raise ValueError("retained_relation_count must be non-negative")
    if downstream_lag_count < 1 or materialized_lag_count < 1:
        raise ValueError("lag counts must be positive")
    if effective_row_count < 1:
        raise ValueError("effective_row_count must be positive")

    retained_feature_count = retained_relation_count
    compute_proxy = retained_relation_count * downstream_lag_count * effective_row_count
    memory_proxy = retained_feature_count * materialized_lag_count * effective_row_count
    return DownstreamResourceProfile(
        budget_ratio=budget_ratio,
        threshold=threshold_for_budget(budget_ratio, config),
        retained_relation_count=retained_relation_count,
        retained_feature_count=retained_feature_count,
        downstream_lag_count=downstream_lag_count,
        materialized_lag_count=materialized_lag_count,
        effective_row_count=effective_row_count,
        downstream_compute_proxy=compute_proxy,
        downstream_memory_proxy=memory_proxy,
        estimated_memory_bytes=memory_proxy * config.bytes_per_value,
    )
