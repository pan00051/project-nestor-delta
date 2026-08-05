# Reproducibility

This file defines how to verify the current environment and Sprint 1 baseline run.

## Sprint 1 Acceptance Commands

Run from a clean checkout:

```bash
python3 --version
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-lock.txt
python scripts/run_baselines.py
```

Expected result:

- Python version is `>=3.9`.
- Virtual environment creation succeeds.
- `requirements-lock.txt` installs successfully.
- Synthetic CSV files are generated under `data/synthetic/`.
- Per-seed metrics are written to `reports/baseline_metrics.csv`.
- Aggregate metrics are written to `reports/baseline_summary.md`.

## Current Dependency Policy

Sprint 1 has no third-party runtime dependencies.

The simple linear regression baseline uses a deterministic standard-library OLS implementation. If a later sprint introduces a package such as NumPy, the dependency must be pinned in `requirements-lock.txt` before any new numbers are reported.

## Output Policy

Sprint 1 writes reproducible generated artifacts.

Tracked outputs:

- `reports/baseline_metrics.csv`
- `reports/baseline_summary.md`

Regenerated but untracked outputs:

- `data/synthetic/synthetic_seed_11.csv`
- `data/synthetic/synthetic_seed_23.csv`
- `data/synthetic/synthetic_seed_37.csv`
- `data/synthetic/synthetic_seed_41.csv`
- `data/synthetic/synthetic_seed_53.csv`
