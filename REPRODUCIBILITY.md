# Reproducibility

This file defines how to verify the Sprint 0 environment and what output is expected at this stage.

## Sprint 0 Acceptance Commands

Run from a clean checkout:

```bash
python3 --version
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-lock.txt
```

Expected Sprint 0 result:

- Python version is `>=3.9`.
- Virtual environment creation succeeds.
- `requirements-lock.txt` installs successfully.
- No baseline metrics are generated in Sprint 0.

## Current Dependency Policy

Sprint 0 has no third-party runtime dependencies.

If Sprint 1 introduces a package such as NumPy for deterministic OLS, the dependency must be pinned in `requirements-lock.txt` before baseline numbers are reported.

## Output Policy

Sprint 0 is documentation and environment groundwork only.

The following outputs are intentionally deferred to Sprint 1:

- generated synthetic CSV files;
- per-seed baseline metrics;
- aggregate baseline summary with mean and min-max range.
