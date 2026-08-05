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

The current sprint is **Sprint 0: lock the evaluation protocol and environment**.

Before writing modeling code, the project needs to freeze:

- the task definition,
- the dataset,
- the metrics,
- the baseline methods,
- the reproducible development environment.

The frozen M0 evaluation protocol is in `EVALUATION.md`.

After that, the first modeling module will be:

- a reusable weighting mechanism,
- followed by a three-variable prediction workflow.

## Reproducible Environment

Sprint 0 intentionally uses no third-party runtime dependencies.

From a clean checkout:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-lock.txt
```

The project requires Python `>=3.9`.

## Repository Layout

```text
.
├── data/synthetic/       # Sprint 1 generated synthetic datasets
├── reports/              # Sprint 1 baseline metrics and summaries
├── scripts/              # Reproducible command-line entry points
├── src/nestor_delta/     # Python package source
├── EVALUATION.md         # Frozen M0 evaluation protocol
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

Sprint 0 groundwork is in place: the evaluation protocol and reproducible environment boundary are defined before implementation.
