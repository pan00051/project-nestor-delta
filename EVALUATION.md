# Nestor Delta Evaluation Protocol v1

> Status: frozen for M0 Sprint 0.
> Scope: this protocol defines the measurement ground for Sprint 1 baselines and later M1 work. Changes after Sprint 0 require an explicit protocol update and must be recorded in `HANDOFF.md`.
> Version: `v1`, covering Sprint 0 and Sprint 1. Any change that would invalidate existing baseline comparisons must create a new protocol version.

## 1. Task Definition

Nestor Delta's first measurable task is one-step-ahead forecasting on a controlled multivariate time series.

Given historical observations up to time `t`, predict the target variable at `t + 1`.

The first target variable is `target`. Predictor variables are synthetic peer signals generated with known relationships to `target`. The task stays in the data layer only: no event interpretation, no causal storytelling, no cross-layer Nestor integration.

Frozen task settings:

- Forecast horizon: `1` step.
- Input window for non-persistence methods: lagged observations from the previous `5` steps.
- Target: `target`.
- Split: chronological split, `70%` train, `15%` validation, `15%` test, with exact row boundaries defined below.
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

### Frozen Synthetic Generation Formula

Sprint 1 must implement the generator exactly as specified here.

Randomness:

- Use Python's standard `random.Random(seed)`.
- Draw Gaussian noise with `rng.gauss(0.0, sigma)`.
- For each time step `t`, draw shocks in this exact order: `eps_a`, `eps_b`, `eps_noise`, `eps_target`.

Initial values:

- Any lagged value before row `0` is `0.0`.
- This means `target[-1]`, `driver_a[-1]`, `driver_b[-1]`, and `driver_b[-2]` are all treated as `0.0`.

For each row `t` from `0` to `599`:

```text
eps_a      ~ Normal(0.0, 0.80)
eps_b      ~ Normal(0.0, 0.80)
eps_noise  ~ Normal(0.0, 1.00)
eps_target ~ Normal(0.0, 0.50)

driver_a[t] = 0.65 * driver_a[t - 1] + eps_a
driver_b[t] = 0.55 * driver_b[t - 1] + eps_b
noise[t]    = eps_noise
target[t]   = 0.55 * target[t - 1]
              + 0.35 * driver_a[t - 1]
              - 0.25 * driver_b[t - 2]
              + eps_target
```

Standardization:

- No standardization is applied to the generated CSV files in M0/M1.
- If a later sprint introduces feature scaling, the scaler must be fit on train rows only and applied forward to validation/test.

Determinism:

- Each seed must produce exactly one deterministic CSV.
- CSV columns must appear in this order: `step`, `target`, `driver_a`, `driver_b`, `noise`.
- Numeric values should be written with a stable precision of at least `10` decimal places.

### Frozen Split and Supervised Sample Rules

For each 600-row generated series:

- Train rows: indices `0` through `419`.
- Validation rows: indices `420` through `509`.
- Test rows: indices `510` through `599`.
- Rows must not be shuffled.

Supervised samples are assigned to splits by the label row index, not by the final feature row.

For horizon `1`, a sample with label row `i` predicts `target[i]` using information no later than row `i - 1`.

For the 5-step lagged linear baseline:

- Earliest usable label row: `5`.
- Train label rows: `5` through `419`, giving `415` supervised samples.
- Validation label rows: `420` through `509`, giving `90` supervised samples.
- Test label rows: `510` through `599`, giving `90` supervised samples.

For the persistence baseline:

- Prediction for label row `i` is `target[i - 1]`.
- It is evaluated on the same label rows as the linear baseline for comparability.

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
   - Prediction for label row `i`: `target_hat[i] = target[i - 1]`.
   - Fit step: none.
   - Evaluation label rows: `510` through `599`.
   - Purpose: the simplest time-series reference point.

2. Simple linear regression baseline
   - Prediction: fit ordinary least squares on lagged values from the previous `5` steps.
   - Intercept: include an intercept column.
   - Fit data: train supervised samples only, label rows `5` through `419`.
   - Validation data: not used for tuning in Sprint 1; report may include it for diagnostics, but final comparison uses test only.
   - Test data: label rows `510` through `599`.
   - Implementation: use `numpy.linalg.lstsq` if NumPy is introduced and pinned; otherwise an equivalent deterministic OLS solver is acceptable. Do not add scikit-learn for Sprint 1 unless a later documented decision explicitly changes this.
   - Feature order:

```text
intercept,
target_lag_1, driver_a_lag_1, driver_b_lag_1, noise_lag_1,
target_lag_2, driver_a_lag_2, driver_b_lag_2, noise_lag_2,
target_lag_3, driver_a_lag_3, driver_b_lag_3, noise_lag_3,
target_lag_4, driver_a_lag_4, driver_b_lag_4, noise_lag_4,
target_lag_5, driver_a_lag_5, driver_b_lag_5, noise_lag_5
```

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

## 6. Leakage Prevention Rules

These rules are part of the locked protocol.

- All fitted baselines must fit on train supervised samples only.
- Validation is reserved for diagnostics or later tuning decisions; it must not affect Sprint 1 test metrics.
- Test is used only for final reporting.
- Rows must remain chronological; no shuffle is allowed.
- Features for label row `i` must use only rows `<= i - 1`.
- Future target values must never be used as features.
- If feature scaling is introduced later, scaling parameters must be fit on train rows only.
- Any change to these rules invalidates comparison with existing baseline reports unless documented as a new evaluation protocol version.

## 7. Explicit Non-Goals

The following are out of scope until their assigned sprint:

- generic relationship-weight mechanism: Sprint 2;
- three-variable weighted prediction workflow: Sprint 3;
- dynamic weight change: Sprint 4;
- ignore value or resource-adaptive pruning: Sprint 5;
- event-impact analysis, causal attribution, or Nestor Insight integration: outside this repo.
