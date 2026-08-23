# Documentation Index

Use the repository root `README.md` for the project overview and quick start.
This directory contains narrower implementation and acceptance references.

## Website

- `WEBSITE_FRONTEND_RUN.md` - local FastAPI and Streamlit commands.
- `WEBSITE_BACKEND_CONTRACT.md` - `delta.report.v1` and endpoint contract.
- `mock_reports_v1.json` - canonical frontend/report states.
- `W5_SCOPE.md` - final display-layer boundary.
- `W5_ACCEPTANCE.md` - latest website acceptance record.
- `W4_ACCEPTANCE.md` - historical frontend-binding acceptance record.

## Relationship Pipeline

- `WEIGHTING.md` - S2 weighting plus the additive S7 transformed path.
- `EVALUATION_POWER.md` - S8 rolling evaluation, intervals, and noise floor.
- `DYNAMIC_WEIGHTS.md` - S4 past-only dynamic weighting.
- `TRUST_GATING.md` - S3.1 pre-model trust gate.
- `RESOURCE_ADAPTIVE_IGNORE.md` - S5 downstream resource adaptation.

## Prediction And Real Data

- `STAGE1.md` - selected lagged prediction.
- `REAL_DATA_CASE_RUNNER.md` - strict author-prepared case format.

Numerical outcomes live under `reports/`; frozen inputs and provenance live under
`cases/`. The root `S7-S10的规则.md` remains the acceptance authority for S7-S10.
