"""Additive bridge from frozen S5 filtering to frozen S6 prediction."""

from __future__ import annotations

import csv
from dataclasses import dataclass, replace
from pathlib import Path
from typing import List, Optional, Sequence, Tuple

from .metrics import mae, rmse
from .real_case_analysis import (
    RealCaseModel,
    fit_real_case_predictor_with_backoff,
    predict_persistence,
    predict_real_case,
)
from .real_data import RealCaseConfig, RealCaseData, real_case_label_rows
from .relation_weights import (
    RelationWeight,
    compute_lagged_relation_weights,
    rank_target_sources,
)
from .resource_adaptive_ignore import (
    DownstreamResourceProfile,
    downstream_profile,
    retain_relations,
    threshold_for_budget,
)
from .s5_config import BUDGET_RATIOS


@dataclass(frozen=True)
class RealBudgetTierResult:
    budget_ratio: float
    threshold: float
    candidate_count: int
    retained_after_threshold: Tuple[RelationWeight, ...]
    admitted_after_cap: Tuple[RelationWeight, ...]
    selected_weights: Tuple[RelationWeight, ...]
    dropped_collinear_sources: Tuple[str, ...]
    model_coefficients: Tuple[float, ...]
    fit_status: str
    persistence_mae: float
    persistence_rmse: float
    delta_mae: Optional[float]
    delta_rmse: Optional[float]
    mae_change_vs_persistence_pct: Optional[float]
    rmse_change_vs_persistence_pct: Optional[float]
    mae_loss_vs_full_budget_pct: Optional[float]
    rmse_loss_vs_full_budget_pct: Optional[float]
    profile: DownstreamResourceProfile
    delta_predictions: Tuple[Optional[float], ...]


@dataclass(frozen=True)
class RealBudgetSweepResult:
    ranking: Tuple[RelationWeight, ...]
    tiers: Tuple[RealBudgetTierResult, ...]
    train_label_rows: Tuple[int, ...]
    test_label_rows: Tuple[int, ...]
    test_dates: Tuple[str, ...]
    actuals: Tuple[float, ...]
    persistence_predictions: Tuple[float, ...]


@dataclass(frozen=True)
class _FrozenTier:
    budget_ratio: float
    threshold: float
    retained_after_threshold: Tuple[RelationWeight, ...]
    admitted_after_cap: Tuple[RelationWeight, ...]
    model: Optional[RealCaseModel]
    profile: DownstreamResourceProfile


def run_real_budget_sweep(
    config: RealCaseConfig, data: RealCaseData
) -> RealBudgetSweepResult:
    """Freeze all budget-tier models on train rows, then evaluate test rows."""
    train_label_rows, test_label_rows = real_case_label_rows(data.dates, config)
    train_end = max(train_label_rows) + 1
    relation_weights = compute_lagged_relation_weights(
        data.rows[:train_end], data.variables, config.lag_window
    )
    ranking = _stable_target_ranking(relation_weights, config.target)

    frozen_tiers: List[_FrozenTier] = []
    for budget_ratio in BUDGET_RATIOS:
        retained = _stable_relations(
            retain_relations(relation_weights, config.target, budget_ratio)
        )
        admitted = retained[: config.max_selected_signals]
        profile = downstream_profile(
            budget_ratio=budget_ratio,
            retained_relation_count=len(admitted),
            downstream_lag_count=config.lag_window,
            materialized_lag_count=config.lag_window,
            effective_row_count=len(train_label_rows),
        )
        model = None
        if admitted:
            model = fit_real_case_predictor_with_backoff(
                data.rows,
                train_label_rows,
                admitted,
                config.target,
                config.lag_window,
            )
        frozen_tiers.append(
            _FrozenTier(
                budget_ratio=budget_ratio,
                threshold=threshold_for_budget(budget_ratio),
                retained_after_threshold=retained,
                admitted_after_cap=admitted,
                model=model,
                profile=profile,
            )
        )

    actuals = tuple(float(data.rows[index][config.target]) for index in test_label_rows)
    persistence_predictions = tuple(
        predict_persistence(data.rows, test_label_rows, config.target)
    )
    persistence_mae = mae(actuals, persistence_predictions)
    persistence_rmse = rmse(actuals, persistence_predictions)

    tiers: List[RealBudgetTierResult] = []
    for frozen in frozen_tiers:
        tier = _evaluate_frozen_tier(
            frozen,
            config,
            data,
            test_label_rows,
            actuals,
            persistence_mae,
            persistence_rmse,
            len(ranking),
        )
        tiers.append(tier)

    full_budget = tiers[0]
    tiers = [
        replace(
            tier,
            mae_loss_vs_full_budget_pct=_relative_change_pct(
                tier.delta_mae, full_budget.delta_mae
            ),
            rmse_loss_vs_full_budget_pct=_relative_change_pct(
                tier.delta_rmse, full_budget.delta_rmse
            ),
        )
        for tier in tiers
    ]

    return RealBudgetSweepResult(
        ranking=ranking,
        tiers=tuple(tiers),
        train_label_rows=train_label_rows,
        test_label_rows=test_label_rows,
        test_dates=tuple(data.dates[index] for index in test_label_rows),
        actuals=actuals,
        persistence_predictions=persistence_predictions,
    )


def write_real_budget_sweep_reports(
    output_dir: Path,
    config: RealCaseConfig,
    data: RealCaseData,
    result: RealBudgetSweepResult,
) -> Tuple[Path, Path, Path]:
    """Write the three deterministic connector reports."""
    output_dir.mkdir(parents=True, exist_ok=True)
    metrics_path = output_dir / "real_budget_sweep_metrics.csv"
    predictions_path = output_dir / "real_budget_sweep_predictions.csv"
    summary_path = output_dir / "real_budget_sweep_summary.md"
    _write_metrics(metrics_path, result)
    _write_predictions(predictions_path, result)
    _write_summary(summary_path, config, data, result)
    return metrics_path, predictions_path, summary_path


def _evaluate_frozen_tier(
    frozen: _FrozenTier,
    config: RealCaseConfig,
    data: RealCaseData,
    test_label_rows: Tuple[int, ...],
    actuals: Tuple[float, ...],
    persistence_mae: float,
    persistence_rmse: float,
    candidate_count: int,
) -> RealBudgetTierResult:
    model = frozen.model
    if model is None:
        fit_status = "baseline_only_no_retained_signal"
        selected_weights: Tuple[RelationWeight, ...] = ()
        dropped_collinear_sources: Tuple[str, ...] = ()
        model_coefficients: Tuple[float, ...] = ()
        predictions: Tuple[Optional[float], ...] = tuple(None for _ in actuals)
        delta_mae = None
        delta_rmse = None
    elif model.fit_status == "baseline_only_no_stable_signal":
        fit_status = model.fit_status
        selected_weights = ()
        dropped_collinear_sources = model.dropped_collinear_sources
        model_coefficients = ()
        predictions = tuple(None for _ in actuals)
        delta_mae = None
        delta_rmse = None
    else:
        fit_status = model.fit_status
        selected_weights = model.selected_weights
        dropped_collinear_sources = model.dropped_collinear_sources
        model_coefficients = model.coefficients
        numeric_predictions = tuple(
            predict_real_case(
                data.rows,
                test_label_rows,
                model,
                config.target,
                config.lag_window,
            )
        )
        predictions = tuple(numeric_predictions)
        delta_mae = mae(actuals, numeric_predictions)
        delta_rmse = rmse(actuals, numeric_predictions)

    return RealBudgetTierResult(
        budget_ratio=frozen.budget_ratio,
        threshold=frozen.threshold,
        candidate_count=candidate_count,
        retained_after_threshold=frozen.retained_after_threshold,
        admitted_after_cap=frozen.admitted_after_cap,
        selected_weights=selected_weights,
        dropped_collinear_sources=dropped_collinear_sources,
        model_coefficients=model_coefficients,
        fit_status=fit_status,
        persistence_mae=persistence_mae,
        persistence_rmse=persistence_rmse,
        delta_mae=delta_mae,
        delta_rmse=delta_rmse,
        mae_change_vs_persistence_pct=_relative_change_pct(
            delta_mae, persistence_mae
        ),
        rmse_change_vs_persistence_pct=_relative_change_pct(
            delta_rmse, persistence_rmse
        ),
        mae_loss_vs_full_budget_pct=None,
        rmse_loss_vs_full_budget_pct=None,
        profile=frozen.profile,
        delta_predictions=predictions,
    )


def _relative_change_pct(
    value: Optional[float], reference: Optional[float]
) -> Optional[float]:
    if value is None or reference is None or reference == 0.0:
        return None
    return (value / reference - 1.0) * 100.0


def _stable_target_ranking(
    relation_weights: Sequence[RelationWeight], target: str
) -> Tuple[RelationWeight, ...]:
    return _stable_relations(rank_target_sources(relation_weights, target))


def _stable_relations(
    relations: Sequence[RelationWeight],
) -> Tuple[RelationWeight, ...]:
    return tuple(
        sorted(
            relations,
            key=lambda relation: (-relation.score, relation.source, relation.lag),
        )
    )


def _write_metrics(path: Path, result: RealBudgetSweepResult) -> None:
    fieldnames = [
        "budget_ratio",
        "threshold",
        "candidate_count",
        "retained_after_threshold_count",
        "admitted_after_cap_count",
        "actual_ols_signal_count",
        "retained_after_threshold_sources",
        "admitted_after_cap_sources",
        "actual_ols_sources",
        "dropped_collinear_sources",
        "fit_status",
        "persistence_mae",
        "persistence_rmse",
        "delta_mae",
        "delta_rmse",
        "mae_change_vs_persistence_pct",
        "rmse_change_vs_persistence_pct",
        "mae_loss_vs_full_budget_pct",
        "rmse_loss_vs_full_budget_pct",
        "downstream_compute_proxy",
        "downstream_memory_proxy",
        "estimated_memory_bytes",
        "test_sample_count",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for tier in result.tiers:
            writer.writerow(
                {
                    "budget_ratio": f"{tier.budget_ratio:.2f}",
                    "threshold": f"{tier.threshold:.10f}",
                    "candidate_count": tier.candidate_count,
                    "retained_after_threshold_count": len(
                        tier.retained_after_threshold
                    ),
                    "admitted_after_cap_count": len(tier.admitted_after_cap),
                    "actual_ols_signal_count": len(tier.selected_weights),
                    "retained_after_threshold_sources": _source_names(
                        tier.retained_after_threshold
                    ),
                    "admitted_after_cap_sources": _source_names(
                        tier.admitted_after_cap
                    ),
                    "actual_ols_sources": _source_names(tier.selected_weights),
                    "dropped_collinear_sources": ";".join(
                        tier.dropped_collinear_sources
                    ),
                    "fit_status": tier.fit_status,
                    "persistence_mae": f"{tier.persistence_mae:.10f}",
                    "persistence_rmse": f"{tier.persistence_rmse:.10f}",
                    "delta_mae": _format_optional(tier.delta_mae),
                    "delta_rmse": _format_optional(tier.delta_rmse),
                    "mae_change_vs_persistence_pct": _format_optional(
                        tier.mae_change_vs_persistence_pct
                    ),
                    "rmse_change_vs_persistence_pct": _format_optional(
                        tier.rmse_change_vs_persistence_pct
                    ),
                    "mae_loss_vs_full_budget_pct": _format_optional(
                        tier.mae_loss_vs_full_budget_pct
                    ),
                    "rmse_loss_vs_full_budget_pct": _format_optional(
                        tier.rmse_loss_vs_full_budget_pct
                    ),
                    "downstream_compute_proxy": tier.profile.downstream_compute_proxy,
                    "downstream_memory_proxy": tier.profile.downstream_memory_proxy,
                    "estimated_memory_bytes": tier.profile.estimated_memory_bytes,
                    "test_sample_count": len(result.test_label_rows),
                }
            )


def _write_predictions(path: Path, result: RealBudgetSweepResult) -> None:
    fieldnames = [
        "budget_ratio",
        "date",
        "actual",
        "persistence",
        "delta_prediction",
        "fit_status",
        "actual_ols_sources",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for tier in result.tiers:
            for index, date in enumerate(result.test_dates):
                writer.writerow(
                    {
                        "budget_ratio": f"{tier.budget_ratio:.2f}",
                        "date": date,
                        "actual": f"{result.actuals[index]:.10f}",
                        "persistence": (
                            f"{result.persistence_predictions[index]:.10f}"
                        ),
                        "delta_prediction": _format_optional(
                            tier.delta_predictions[index]
                        ),
                        "fit_status": tier.fit_status,
                        "actual_ols_sources": _source_names(
                            tier.selected_weights
                        ),
                    }
                )


def _write_summary(
    path: Path,
    config: RealCaseConfig,
    data: RealCaseData,
    result: RealBudgetSweepResult,
) -> None:
    lines = [
        f"# Real Case Budget Sweep: {config.case_name}",
        "",
        "Scope: a fixed five-tier pressure scan connecting S5 relation filtering to the S6 prediction path. Results describe co-movement and out-of-sample predictive usefulness only; they do not establish causality.",
        "",
        f"- Target: `{config.target}`",
        f"- Candidate signals: {len(config.candidate_signals)}",
        f"- Rows: {len(data.rows)}",
        f"- Train labels: {len(result.train_label_rows)}",
        f"- Test labels: {len(result.test_label_rows)}",
        f"- Lag window: {config.lag_window}",
        f"- Maximum admitted signals: {config.max_selected_signals}",
        "- Baseline comparator: persistence",
        "",
        "## Fixed Budget Tiers",
        "",
        "| Budget | Threshold | Candidates | After threshold | After cap | Actual OLS | MAE change vs persistence | Fit status |",
        "|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for tier in result.tiers:
        lines.append(
            "| {budget:.2f} | {threshold:.2f} | {candidates} | {retained} | "
            "{admitted} | {actual} | {mae_change} | `{status}` |".format(
                budget=tier.budget_ratio,
                threshold=tier.threshold,
                candidates=tier.candidate_count,
                retained=len(tier.retained_after_threshold),
                admitted=len(tier.admitted_after_cap),
                actual=len(tier.selected_weights),
                mae_change=_display_pct(tier.mae_change_vs_persistence_pct),
                status=tier.fit_status,
            )
        )
    lines.extend(
        [
            "",
            "## Interpretation Boundary",
            "",
            "- All five budget tiers were fixed before evaluation. This report does not select or announce a winning tier from test results.",
            "- Relation scoring, threshold filtering, ranking, capping, collinearity backoff, and model fitting use train rows only. All tier signal sets and coefficients are frozen before test evaluation begins.",
            "- The `0.06` minimum threshold is a frozen S5 pressure-scan parameter derived from the synthetic benchmark. It is not a universal real-data noise cutoff.",
            "- Trends and seasonality in real data can raise relation scores, including scores for relationships that do not generalize.",
            "- Downstream proxies use the number admitted after the cap. They exclude upstream relation discovery, target-history features, the intercept, and measured wall-clock runtime.",
            "- Empty Delta fields mean no Delta model was fitted for that tier; baseline values are not copied into Delta columns.",
        ]
    )
    if config.notes:
        lines.extend(["", "## Notes", "", config.notes])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _source_names(weights: Sequence[RelationWeight]) -> str:
    return ";".join(weight.source for weight in weights)


def _format_optional(value: Optional[float]) -> str:
    return "" if value is None else f"{value:.10f}"


def _display_pct(value: Optional[float]) -> str:
    return "n/a" if value is None else f"{value:.2f}%"
