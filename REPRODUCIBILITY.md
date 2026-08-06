# Reproducibility

This file defines how to verify the environment and all completed workflows through Sprint 4 dynamic weights.

## Acceptance Commands

Run from a clean checkout:

```bash
python3 --version
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

Expected result:

- Python version is `>=3.9`.
- Virtual environment creation succeeds.
- `requirements-lock.txt` installs successfully.
- Synthetic CSV files are generated under `data/synthetic/`.
- Per-seed metrics are written to `reports/baseline_metrics.csv`.
- Aggregate metrics are written to `reports/baseline_summary.md`.
- Unit tests pass, including deterministic generation and OLS coefficient recovery.
- Relation-weight details are written to `reports/weight_validation.csv`.
- Relation-weight summary is written to `reports/weight_validation_summary.md`.
- Stage 1 metrics are written to `reports/stage1_metrics.csv`.
- Stage 1 selected sources are written to `reports/stage1_selected_sources.csv`.
- Stage 1 summary is written to `reports/stage1_summary.md`.
- Trust-gating metrics, admissions, sensitivity checks, and summary are written under `reports/trust_gating_*`.
- Drift data and separate coefficient truth sidecars are generated under `data/synthetic_drift/`.
- Dynamic-weight metrics, per-step trajectory, tracking checks, and summary are written under `reports/dynamic_weight_*`.
- Unit tests pass, including deterministic drift generation, causal window exclusion, known drift tracking, and static/dynamic prediction comparison.

## Current Dependency Policy

The completed project through Sprint 4 dynamic weights has no third-party runtime dependencies.

The simple linear regression baseline uses a deterministic standard-library OLS implementation. Relation weighting, Stage 1 prediction, trust gating, drift generation, and rolling adaptation also use only the Python standard library. If a later sprint introduces a package such as NumPy, the dependency must be pinned in `requirements-lock.txt` before any new numbers are reported.

## Test Policy

The test suite is standard-library only and can be run with:

```bash
python -m unittest discover -s tests
```

Current permanent checks:

- same-seed synthetic generation produces identical CSV bytes;
- the linear regression baseline recovers the known synthetic drivers on the frozen seed `11` training split within documented tolerance;
- the S4 rolling window excludes the current and future rows;
- all five drift seeds move in the known direction and dynamic mean MAE/RMSE beat static weights.

## Output Policy

Sprint 1 and Sprint 2 write reproducible generated artifacts.

Tracked outputs:

- `reports/baseline_metrics.csv`
- `reports/baseline_summary.md`
- `reports/weight_validation.csv`
- `reports/weight_validation_summary.md`
- `reports/stage1_metrics.csv`
- `reports/stage1_selected_sources.csv`
- `reports/stage1_summary.md`
- `reports/trust_gating_metrics.csv`
- `reports/trust_gating_admissions.csv`
- `reports/trust_gating_sensitivity.csv`
- `reports/trust_gating_summary.md`
- `reports/dynamic_weight_metrics.csv`
- `reports/dynamic_weight_trajectory.csv`
- `reports/dynamic_weight_tracking.csv`
- `reports/dynamic_weight_summary.md`

Regenerated but untracked outputs:

- `data/synthetic/synthetic_seed_11.csv`
- `data/synthetic/synthetic_seed_23.csv`
- `data/synthetic/synthetic_seed_37.csv`
- `data/synthetic/synthetic_seed_41.csv`
- `data/synthetic/synthetic_seed_53.csv`
- `data/synthetic_drift/synthetic_drift_seed_<seed>.csv`
- `data/synthetic_drift/synthetic_drift_truth_seed_<seed>.csv`
