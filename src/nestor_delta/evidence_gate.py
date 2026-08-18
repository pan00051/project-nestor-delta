"""S10 Evidence Gate v1 for relation selection."""

from __future__ import annotations

import math
from dataclasses import dataclass
from statistics import NormalDist
from typing import Sequence, Tuple

from .noise_floor import correlation_noise_floor
from .relation_weights import RelationWeight


@dataclass(frozen=True)
class EvidenceDecision:
    """One relation plus the evidence terms that decided selection."""

    relation: RelationWeight
    effect_size: float
    p_value: float
    fdr_threshold: float
    sample_support: float
    stability: float | None
    uncertainty: float | None
    selected: bool
    reason: str


@dataclass(frozen=True)
class EvidenceGateResult:
    """Evidence-gated selection result for one target."""

    decisions: Tuple[EvidenceDecision, ...]
    selected_relations: Tuple[RelationWeight, ...]
    fit_status: str


def select_relations_with_evidence(
    relations: Sequence[RelationWeight],
    *,
    max_lag: int,
    target: str | None = None,
    alpha: float = 0.05,
    min_stability: float = 0.45,
    max_uncertainty: float = 0.20,
    min_sample_support: float = 0.50,
    reference_sample_count: int | None = None,
) -> EvidenceGateResult:
    """Select relations using score, S9 stability, sample support, and FDR.

    The gate consumes relationship uncertainty only. It deliberately has no
    prediction-error input, so failed predictions cannot loosen selection.
    """
    if max_lag < 1:
        raise ValueError("max_lag must be at least 1")
    if not 0.0 < alpha < 1.0:
        raise ValueError("alpha must lie strictly between 0 and 1")

    candidates = tuple(
        relation for relation in relations if target is None or relation.target == target
    )
    if not candidates:
        return EvidenceGateResult((), (), "baseline_only_no_evidence")

    reference = reference_sample_count or max(
        relation.sample_count for relation in candidates
    )
    if reference <= 0:
        raise ValueError("reference_sample_count must be positive")

    p_values = [_correlation_p_value(relation.score, relation.sample_count) for relation in candidates]
    thresholds = _benjamini_hochberg_thresholds(p_values, alpha)
    scored = []
    pair_count = max(1, len({(relation.source, relation.target) for relation in candidates}))
    comparisons = max_lag * pair_count
    for relation, p_value, fdr_threshold in zip(candidates, p_values, thresholds):
        noise_floor = correlation_noise_floor(
            relation.sample_count, comparisons=comparisons, alpha=alpha
        ).threshold
        effect_size = relation.score / noise_floor if noise_floor > 0.0 else 0.0
        sample_support = min(1.0, relation.sample_count / reference)
        selected = (
            p_value <= fdr_threshold
            and relation.stability is not None
            and relation.stability >= min_stability
            and relation.uncertainty is not None
            and relation.uncertainty <= max_uncertainty
            and sample_support >= min_sample_support
        )
        reason = _decision_reason(
            selected,
            p_value,
            fdr_threshold,
            relation,
            min_stability,
            max_uncertainty,
            sample_support,
            min_sample_support,
        )
        scored.append(
            EvidenceDecision(
                relation=RelationWeight(
                    source=relation.source,
                    target=relation.target,
                    lag=relation.lag,
                    weight=relation.weight,
                    score=relation.score,
                    sample_count=relation.sample_count,
                    transform=relation.transform,
                    stability=relation.stability,
                    uncertainty=relation.uncertainty,
                    selected=selected,
                ),
                effect_size=effect_size,
                p_value=p_value,
                fdr_threshold=fdr_threshold,
                sample_support=sample_support,
                stability=relation.stability,
                uncertainty=relation.uncertainty,
                selected=selected,
                reason=reason,
            )
        )

    decisions = tuple(sorted(scored, key=lambda item: (-item.relation.score, item.relation.source)))
    selected_relations = tuple(decision.relation for decision in decisions if decision.selected)
    fit_status = "fit" if selected_relations else "baseline_only_no_evidence"
    return EvidenceGateResult(decisions, selected_relations, fit_status)


def precision_recall(
    selected_sources: Sequence[str], true_sources: Sequence[str]
) -> Tuple[float, float]:
    """Return precision and recall for selected source names."""
    selected = set(selected_sources)
    truth = set(true_sources)
    if not selected:
        precision = 1.0 if not truth else 0.0
    else:
        precision = len(selected & truth) / len(selected)
    recall = 1.0 if not truth else len(selected & truth) / len(truth)
    return precision, recall


def fixed_threshold_selection(
    relations: Sequence[RelationWeight],
    *,
    threshold: float = 0.06,
) -> Tuple[RelationWeight, ...]:
    """Frozen fixed-score threshold baseline for S10 comparisons."""
    return tuple(relation for relation in relations if relation.score > threshold)


def _benjamini_hochberg_thresholds(
    p_values: Sequence[float], alpha: float
) -> Tuple[float, ...]:
    indexed = sorted(enumerate(p_values), key=lambda item: item[1])
    accepted_cutoff = 0.0
    total = len(indexed)
    for rank, (_, p_value) in enumerate(indexed, start=1):
        threshold = alpha * rank / total
        if p_value <= threshold:
            accepted_cutoff = p_value
    thresholds = [accepted_cutoff for _ in p_values]
    return tuple(thresholds)


def _correlation_p_value(score: float, sample_count: int) -> float:
    if sample_count <= 3:
        return 1.0
    clipped = min(0.999999, max(0.0, abs(score)))
    z_score = math.atanh(clipped) * math.sqrt(sample_count - 3)
    return 2.0 * (1.0 - NormalDist().cdf(abs(z_score)))


def _decision_reason(
    selected: bool,
    p_value: float,
    fdr_threshold: float,
    relation: RelationWeight,
    min_stability: float,
    max_uncertainty: float,
    sample_support: float,
    min_sample_support: float,
) -> str:
    if selected:
        return "selected"
    if p_value > fdr_threshold:
        return "below_fdr_corrected_effect"
    if relation.stability is None or relation.stability < min_stability:
        return "insufficient_stability"
    if relation.uncertainty is None or relation.uncertainty > max_uncertainty:
        return "excess_relationship_uncertainty"
    if sample_support < min_sample_support:
        return "insufficient_sample_support"
    return "not_selected"
