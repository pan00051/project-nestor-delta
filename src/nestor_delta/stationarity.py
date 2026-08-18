"""S7 explicit transforms and persistence diagnostics."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, Iterable, List, Mapping, Sequence, Tuple

from .relation_weights import NumericRow, RelationWeight, _pearson_correlation

TRANSFORMS = {"none", "diff", "log_diff"}
PERSISTENCE_ACF_THRESHOLD = 0.95


@dataclass(frozen=True)
class SignalDiagnostic:
    signal: str
    transform: str | None
    level_lag1_acf: float
    highly_persistent_risk: bool


def validate_transform_declarations(
    variables: Iterable[str], transforms: Mapping[str, str]
) -> Dict[str, str]:
    variable_names = tuple(variables)
    missing = sorted(name for name in variable_names if name not in transforms)
    extra = sorted(name for name in transforms if name not in set(variable_names))
    if missing:
        raise ValueError(f"missing transform declarations for: {missing}")
    if extra:
        raise ValueError(f"transform declarations contain unknown signals: {extra}")
    invalid = {
        name: value for name, value in transforms.items() if value not in TRANSFORMS
    }
    if invalid:
        raise ValueError(
            "transform declarations must be one of none/diff/log_diff: "
            f"{invalid}"
        )
    return {name: transforms[name] for name in variable_names}


def signal_diagnostics(
    rows: Sequence[NumericRow],
    variables: Iterable[str],
    transforms: Mapping[str, str] | None = None,
) -> Tuple[SignalDiagnostic, ...]:
    diagnostics: List[SignalDiagnostic] = []
    for variable in variables:
        values = [float(row[variable]) for row in rows]
        acf = lag1_acf(values)
        diagnostics.append(
            SignalDiagnostic(
                signal=variable,
                transform=None if transforms is None else transforms.get(variable),
                level_lag1_acf=acf,
                highly_persistent_risk=abs(acf) > PERSISTENCE_ACF_THRESHOLD,
            )
        )
    return tuple(diagnostics)


def compute_transformed_relation_weights(
    rows: Sequence[NumericRow],
    variables: Iterable[str],
    max_lag: int,
    transforms: Mapping[str, str],
) -> List[RelationWeight]:
    """Compute S7 short-run relation weights after explicit per-signal transforms."""
    variable_names = tuple(variables)
    declarations = validate_transform_declarations(variable_names, transforms)
    _guard_persistent_level_without_declaration(rows, variable_names, declarations)
    transformed = {
        variable: _transform_series(
            [float(row[variable]) for row in rows], declarations[variable]
        )
        for variable in variable_names
    }
    transform_label = _relation_transform_label(declarations.values())

    weights: List[RelationWeight] = []
    for target in variable_names:
        for source in variable_names:
            if source == target:
                continue
            weights.append(
                _best_transformed_weight_for_pair(
                    transformed[source],
                    transformed[target],
                    source,
                    target,
                    max_lag,
                    transform_label,
                )
            )
    return weights


def lag1_acf(values: Sequence[float]) -> float:
    if len(values) < 2:
        raise ValueError("lag-1 ACF requires at least two observations")
    return _pearson_correlation(values[:-1], values[1:])


def _guard_persistent_level_without_declaration(
    rows: Sequence[NumericRow],
    variables: Tuple[str, ...],
    transforms: Mapping[str, str],
) -> None:
    risky_level_signals = [
        diagnostic.signal
        for diagnostic in signal_diagnostics(rows, variables, transforms)
        if diagnostic.highly_persistent_risk and transforms[diagnostic.signal] == "none"
    ]
    if risky_level_signals:
        raise ValueError(
            "S7 refuses level scoring for highly persistent signals without an "
            "explicit non-level transform declaration: "
            f"{sorted(risky_level_signals)}"
        )


def _transform_series(values: Sequence[float], transform: str) -> Tuple[float | None, ...]:
    if transform == "none":
        return tuple(values)
    transformed: List[float | None] = [None]
    previous = float(values[0])
    for value in values[1:]:
        current = float(value)
        if transform == "diff":
            transformed.append(current - previous)
        elif transform == "log_diff":
            if current <= 0.0 or previous <= 0.0:
                raise ValueError("log_diff requires strictly positive values")
            transformed.append(math.log(current) - math.log(previous))
        else:
            raise ValueError(f"unsupported transform: {transform}")
        previous = current
    return tuple(transformed)


def _best_transformed_weight_for_pair(
    source_values: Sequence[float | None],
    target_values: Sequence[float | None],
    source: str,
    target: str,
    max_lag: int,
    transform_label: str,
) -> RelationWeight:
    if max_lag < 1:
        raise ValueError("max_lag must be at least 1")
    best: RelationWeight | None = None
    for lag in range(1, max_lag + 1):
        left, right = _lagged_transformed_pair_values(source_values, target_values, lag)
        coefficient = _pearson_correlation(left, right)
        candidate = RelationWeight(
            source=source,
            target=target,
            lag=lag,
            weight=coefficient,
            score=abs(coefficient),
            sample_count=len(left),
            transform=transform_label,
        )
        if best is None or candidate.score > best.score:
            best = candidate
    if best is None:
        raise ValueError("no transformed relation weight could be computed")
    return best


def _lagged_transformed_pair_values(
    source_values: Sequence[float | None],
    target_values: Sequence[float | None],
    lag: int,
) -> Tuple[List[float], List[float]]:
    left: List[float] = []
    right: List[float] = []
    for index in range(lag, len(target_values)):
        source_value = source_values[index - lag]
        target_value = target_values[index]
        if source_value is None or target_value is None:
            continue
        left.append(float(source_value))
        right.append(float(target_value))
    if not left:
        raise ValueError("no aligned transformed samples for lag")
    return left, right


def _relation_transform_label(transforms: Iterable[str]) -> str:
    unique = tuple(sorted(set(transforms)))
    if len(unique) == 1:
        return unique[0]
    return "mixed:" + ",".join(unique)
