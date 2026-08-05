# Nestor Delta Evaluation Protocol

> Status: frozen for M0 Sprint 0.
> Scope: this protocol defines the measurement ground for Sprint 1 baselines and later M1 work. Changes after Sprint 0 require an explicit protocol update and must be recorded in `HANDOFF.md`.

## 1. Task Definition

Nestor Delta's first measurable task is one-step-ahead forecasting on a controlled multivariate time series.

Given historical observations up to time `t`, predict the target variable at `t + 1`.

The first target variable is `target`. Predictor variables are synthetic peer signals generated with known relationships to `target`. The task stays in the data layer only: no event interpretation, no causal storytelling, no cross-layer Nestor integration.

Frozen task settings:

- Forecast horizon: `1` step.
- Input window for non-persistence methods: lagged observations from the previous `5` steps.
- Target: `target`.
- Split: chronological split, `70%` train, `15%` validation, `15%` test.
- Evaluation set: test split only.
- Repeated runs: `5` fixed seeds, reported as mean plus min-max range.

## 2. Data Plan

The first dataset is a synthetic multivariate time series.

Reason for choosing synthetic data first:

- relationships are controlled and auditable;
- baseline behavior is easier to interpret;
- later relationship-weight mechanisms can be tested against known signal structure;
- reproducibility does not depend on a third-party data source.

The Sprint 1 generator should create one CSV per seed under `data/synthetic/` with these columns:

- `step`: integer time index.
- `target`: the forecast target.
- `driver_a`: a leading signal with positive relationship to `target`.
- `driver_b`: a leading signal with negative or delayed relationship to `target`.
- `noise`: weak unrelated signal.

Frozen data settings:

- Number of runs: `5`.
- Seeds: `11`, `23`, `37`, `41`, `53`.
- Series length per run: `600` rows.
- Data frequency: abstract equal-spaced steps, not tied to calendar time.
- Missing values: none in M0/M1.
- Dynamic drift: excluded in M0/M1; reserved for M2.
- Ignore-value / resource-adaptive pruning: excluded in M0/M1; reserved for M2.

Future note: a real public multivariate time-series dataset may be added after the synthetic baseline is stable, to strengthen portfolio credibility. That is not part of Sprint 0 or Sprint 1.

## 3. Metrics

Primary metrics:

- MAE: mean absolute error on the test split.
- RMSE: root mean squared error on the test split.

Reporting rule:

- For each baseline, report per-seed MAE and RMSE.
- Report aggregate mean and min-max range across the five frozen seeds.
- Do not claim improvement from a single run.

Later metrics:

- Runtime and memory can be added once there is a meaningful model comparison.
- Relationship-weight quality metrics belong to Sprint 2 and must not be introduced in Sprint 1.

## 4. Baseline List

Sprint 1 must implement at least these two baselines:

1. Persistence / previous value baseline
   - Prediction: `target[t + 1] = target[t]`.
   - Purpose: the simplest time-series reference point.

2. Simple linear regression baseline
   - Prediction: fit ordinary least squares on lagged values from the previous `5` steps.
   - Features: lagged `target`, `driver_a`, `driver_b`, and `noise`.
   - Purpose: a simple statistical baseline before any Nestor Delta relationship-weight mechanism exists.

Optional later baseline:

- VAR-style baseline can be added only after the two required baselines are reproducible.

## 5. Reproducibility Contract

The full Sprint 1 baseline run must be reproducible from a clean checkout with:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-lock.txt
```

At Sprint 0, `requirements-lock.txt` intentionally contains no third-party runtime dependencies. If Sprint 1 adds dependencies, they must be pinned there.

Expected Sprint 1 command shape:

```bash
python scripts/run_baselines.py
```

Expected Sprint 1 outputs:

- synthetic CSV files in `data/synthetic/`;
- per-seed baseline metrics in `reports/baseline_metrics.csv`;
- aggregate baseline summary in `reports/baseline_summary.md`.

## 6. Explicit Non-Goals

The following are out of scope until their assigned sprint:

- generic relationship-weight mechanism: Sprint 2;
- three-variable weighted prediction workflow: Sprint 3;
- dynamic weight change: Sprint 4;
- ignore value or resource-adaptive pruning: Sprint 5;
- event-impact analysis, causal attribution, or Nestor Insight integration: outside this repo.
