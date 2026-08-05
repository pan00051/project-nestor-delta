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

The current sprint is **Sprint 2: generic relation weighting mechanism**.

Before writing modeling code, the project needs to freeze:

- the task definition,
- the dataset,
- the metrics,
- the baseline methods,
- the reproducible development environment.

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

## Repository Layout

```text
.
├── data/synthetic/       # Generated synthetic datasets
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

Sprint 3 is complete: the weighted three-variable Stage 1 prediction workflow is implemented and evaluated under the frozen M0 protocol.
