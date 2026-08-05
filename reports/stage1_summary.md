# Sprint 3 Stage 1 Prediction Summary

Protocol: `EVALUATION.md` v1 frozen split and metrics.

Stage 1 combines Sprint 2 relation weights with Sprint 1 OLS prediction.
For each seed, relation weights are computed on train rows only; the top two sources for `target` are selected; the predictor uses lagged `target` plus the two selected source variables.

| Method | Runs | MAE mean | MAE range | RMSE mean | RMSE range |
|---|---:|---:|---:|---:|---:|
| linear_regression | 5 | 0.428163 | 0.381239-0.470460 | 0.540204 | 0.478609-0.592253 |
| persistence | 5 | 0.566021 | 0.508144-0.624679 | 0.703043 | 0.632300-0.789040 |
| stage1_weighted_three_variable | 5 | 0.422277 | 0.375342-0.457150 | 0.532636 | 0.470656-0.589775 |

## Improvement

- MAE vs persistence: 25.40% lower.
- RMSE vs persistence: 24.24% lower.
- MAE vs Sprint 1 linear regression: 1.37% lower.
- RMSE vs Sprint 1 linear regression: 1.40% lower.

## Boundary

This is a fixed Stage 1 workflow. It does not implement dynamic weights, ignore values, resource adaptation, or event attribution.
