# Nestor Delta

Nestor Delta is the data-layer module of the Nestor project.

Its goal is to analyze how multiple signals relate to each other over time: which variables seem connected, how strong those connections are, when those relationships change, and which weak signals can be safely ignored so the system stays focused.

This repository is not trying to build a general AI assistant or invent a new algorithm. It is a portfolio-grade engineering project: define the problem clearly, build the module in a modular way, test whether it works, and explain the result honestly.

## What Problem It Solves

Many real-world decisions depend on moving signals:

- market indicators,
- product metrics,
- user behavior,
- operational data,
- public events,
- business KPIs.

The hard part is not just seeing that numbers changed. The hard part is understanding which changes matter, which relationships are stable, which ones are drifting, and which signals are too weak or noisy to deserve attention.

Nestor Delta focuses on that data-layer problem.

## Simple Example

Imagine tracking five business metrics every day:

- website visits,
- trial signups,
- paid conversions,
- ad spend,
- customer complaints.

Nestor Delta asks questions like:

- Which signals are most related to paid conversions?
- Did that relationship change recently?
- Are some signals currently too weak to matter?
- Can the system ignore low-value signals without losing too much accuracy?

The final output should help a later layer of Nestor explain what changed and why.

## Role Inside Nestor

Nestor is designed as three independently deliverable projects:

| Project | Layer | Purpose |
|---------|-------|---------|
| Nestor Delta | Data layer | Models changing relationships between variables |
| Nestor Insight | Information layer | Evaluates event impact and importance |
| Nestor | Full system | Combines data relationships with event analysis |

This repository is only for **Nestor Delta**.

## Current Focus

The current focus is not to build everything at once.

**Sprint 4 dynamic weight drift is implemented and has passed its engineering acceptance checks.** It adds a parallel known-drift benchmark without changing the frozen S0-S3.1 data or logic.

The frozen M0 evaluation protocol is in `EVALUATION.md`.

The first reusable capability module is:

- a layer-independent relation weighting mechanism.

Its interface and boundaries are documented in `docs/WEIGHTING.md`.

## Reproducible Environment

Sprint 2 intentionally uses no third-party runtime dependencies.

From a clean checkout:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-lock.txt
python scripts/run_baselines.py
python scripts/run_weights.py
python scripts/run_stage1.py
python scripts/run_trust_gating.py
python scripts/run_dynamic_weights.py
python -m unittest discover -s tests
```

The project requires Python `>=3.9`.

Acceptance commands and expected outputs are listed in `REPRODUCIBILITY.md`.

## Sprint 1 Baseline Results

The baseline report is saved in `reports/baseline_summary.md`.

Current test-set results across the five frozen seeds:

| Baseline | MAE mean | MAE range | RMSE mean | RMSE range |
|---|---:|---:|---:|---:|
| linear_regression | 0.428163 | 0.381239-0.470460 | 0.540204 | 0.478609-0.592253 |
| persistence | 0.566021 | 0.508144-0.624679 | 0.703043 | 0.632300-0.789040 |

## Sprint 2 Relation Weight Results

The relation weighting module computes directed lagged Pearson weights. It is standalone and does not perform prediction.

Validation report: `reports/weight_validation_summary.md`.

Current target-source ranking across the five frozen seeds:

| Source | Mean rank | Rank range | Mean score | Score range |
|---|---:|---:|---:|---:|
| driver_a | 1.00 | 1-1 | 0.595528 | 0.548573-0.663159 |
| driver_b | 2.00 | 2-2 | 0.393421 | 0.331254-0.464283 |
| noise | 3.00 | 3-3 | 0.059127 | 0.020952-0.093188 |

## Sprint 3 Stage 1 Results

Stage 1 combines Sprint 2 relation weights with Sprint 1 OLS prediction. It selects the top two train-only sources for `target`, then predicts with lagged `target` plus those two weighted source histories.

Report: `reports/stage1_summary.md`.

Current test-set results across the five frozen seeds:

| Method | MAE mean | MAE range | RMSE mean | RMSE range |
|---|---:|---:|---:|---:|
| stage1_weighted_three_variable | 0.422277 | 0.375342-0.457150 | 0.532636 | 0.470656-0.589775 |
| linear_regression | 0.428163 | 0.381239-0.470460 | 0.540204 | 0.478609-0.592253 |
| persistence | 0.566021 | 0.508144-0.624679 | 0.703043 | 0.632300-0.789040 |

Mean improvement: Stage 1 is `25.40%` lower MAE than persistence and `1.37%` lower MAE than the Sprint 1 linear regression baseline.

## S3.1 Static Trust-Gating Results

Trust gating applies signed, piecewise-linear source admissions before OLS and combines admitted sources into shared relation signals. This prevents OLS from independently undoing each source's trust value.

Report: `reports/trust_gating_summary.md`. Interface and rationale: `docs/TRUST_GATING.md`.

| Mode | MAE mean | MAE range | RMSE mean | RMSE range |
|---|---:|---:|---:|---:|
| sprint3_ols | 0.422277 | 0.375342-0.457150 | 0.532636 | 0.470656-0.589775 |
| trust_gated_ols | 0.454786 | 0.415817-0.492024 | 0.568517 | 0.518068-0.634403 |

The gated mode is less accurate on this fixed dataset, which is reported as the trade-off. Its purpose is verified separately: changing only weak-source `driver_b` trust to `1.0` changes gated predictions by `0.0774200737` on average, while noise remains blocked and the frozen Sprint 3 OLS mode remains unchanged to 10 decimal places.

## Sprint 4 Dynamic Weight Results

Sprint 4 wraps the frozen static relation-weight mechanism in a 120-row causal sliding window. Its separate synthetic benchmark holds the `driver_a` lag-1 coefficient at `0.15` through train, then increases it linearly to `0.65` through validation and test.

Report: `reports/dynamic_weight_summary.md`. Interface and leakage boundary: `docs/DYNAMIC_WEIGHTS.md`.

| Mode | MAE mean | MAE range | RMSE mean | RMSE range |
|---|---:|---:|---:|---:|
| dynamic_weights | 0.506484 | 0.463798-0.572600 | 0.640280 | 0.580674-0.715281 |
| static_weights | 0.547689 | 0.490096-0.624914 | 0.683878 | 0.636739-0.768990 |

The dynamic `driver_a -> target` weight moves upward from test start to test end for all five frozen drift seeds. Dynamic weights reduce mean MAE by `7.52%` and mean RMSE by `6.38%` versus the static comparator.

## Repository Layout

```text
.
├── data/synthetic/       # Original generated synthetic datasets
├── data/synthetic_drift/ # Parallel S4 drift data and truth sidecars
├── docs/                 # Module interface notes
├── reports/              # Baseline metrics and summaries
├── scripts/              # Reproducible command-line entry points
├── src/nestor_delta/     # Python package source
├── EVALUATION.md         # Frozen M0 evaluation protocol
├── REPRODUCIBILITY.md    # Environment verification and output expectations
├── requirements-lock.txt # Pinned environment dependencies
└── pyproject.toml        # Project metadata and Python version boundary
```

## Project Rules

This repo uses three operating documents:

- `BLUEPRINT.md`: the project constitution and source of truth.
- `HANDOFF.md`: current progress, next step, and pending decisions.
- `RUNBOOK.md`: how the collaboration workflow operates.

Before doing project work, read `BLUEPRINT.md` and `HANDOFF.md`.

## Status

Sprint 4 dynamic weight drift is implemented and reproducibly meets its frozen tracking and prediction criteria. Sprint 5 resource-adaptive ignore values have not started.
