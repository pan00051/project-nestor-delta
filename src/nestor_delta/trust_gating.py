"""Layer-independent trust gates for signed relation weights."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence, Tuple

from .relation_weights import RelationWeight, rank_target_sources


@dataclass(frozen=True)
class TrustGateConfig:
    """Thresholds for deterministic piecewise-linear admission."""

    ignore_threshold: float = 0.15
    full_trust_threshold: float = 0.50

    def __post_init__(self) -> None:
        if not 0.0 <= self.ignore_threshold < self.full_trust_threshold <= 1.0:
            raise ValueError(
                "thresholds must satisfy 0 <= ignore_threshold "
                "< full_trust_threshold <= 1"
            )


@dataclass(frozen=True)
class TrustGate:
    """Admission decision for one signed source-to-target relation."""

    source: str
    target: str
    lag: int
    direction: float
    trust: float
    admission: float
    sample_count: int


DEFAULT_GATE_CONFIG = TrustGateConfig()


def linear_admission(trust: float, config: TrustGateConfig = DEFAULT_GATE_CONFIG) -> float:
    """Map absolute trust to [0, 1] with a deterministic linear ramp."""
    if trust < 0.0 or trust > 1.0:
        raise ValueError("trust must be between 0 and 1")
    if trust <= config.ignore_threshold:
        return 0.0
    if trust >= config.full_trust_threshold:
        return 1.0
    return (trust - config.ignore_threshold) / (
        config.full_trust_threshold - config.ignore_threshold
    )


def build_trust_gates(
    weights: Sequence[RelationWeight],
    target: str,
    config: TrustGateConfig = DEFAULT_GATE_CONFIG,
) -> Tuple[TrustGate, ...]:
    """Build ranked gates for every candidate source of one target."""
    gates = []
    for weight in rank_target_sources(weights, target):
        direction = -1.0 if weight.weight < 0.0 else 1.0
        gates.append(
            TrustGate(
                source=weight.source,
                target=weight.target,
                lag=weight.lag,
                direction=direction,
                trust=weight.score,
                admission=linear_admission(weight.score, config),
                sample_count=weight.sample_count,
            )
        )
    if not gates:
        raise ValueError(f"no relation weights found for target {target!r}")
    return tuple(gates)


def combine_gated_signals(row: Mapping[str, float], gates: Sequence[TrustGate]) -> float:
    """Combine source values so OLS cannot undo their relative admissions."""
    return sum(
        gate.direction * gate.admission * float(row[gate.source])
        for gate in gates
    )
