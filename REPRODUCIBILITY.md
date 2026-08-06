# Reproducibility

This file defines how to verify the environment and all completed static evaluation workflows through trust gating.

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
- Unit tests pass, including deterministic generation, OLS coefficient recovery, relation-weight determinism, known lag driver ranking, trust-gate correctness, and prediction sensitivity.

## Current Dependency Policy

The completed project through static Sprint 4 trust gating has no third-party runtime dependencies.

The simple linear regression baseline uses a deterministic standard-library OLS implementation. Relation weighting, Stage 1 prediction, and trust gating also use only the Python standard library. If a later sprint introduces a package such as NumPy, the dependency must be pinned in `requirements-lock.txt` before any new numbers are reported.

## Test Policy

The test suite is standard-library only and can be run with:

```bash
python -m unittest discover -s tests
```

Current permanent checks:

- same-seed synthetic generation produces identical CSV bytes;
- the linear regression baseline recovers the known synthetic drivers on the frozen seed `11` training split within documented tolerance.

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

Regenerated but untracked outputs:

- `data/synthetic/synthetic_seed_11.csv`
- `data/synthetic/synthetic_seed_23.csv`
- `data/synthetic/synthetic_seed_37.csv`
- `data/synthetic/synthetic_seed_41.csv`
- `data/synthetic/synthetic_seed_53.csv`
