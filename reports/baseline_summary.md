# Sprint 1 Baseline Summary

Protocol: `EVALUATION.md` M0 frozen protocol.

Rows are test-set metrics across the five fixed seeds. Ranges are min-max.

| Baseline | Runs | MAE mean | MAE range | RMSE mean | RMSE range |
|---|---:|---:|---:|---:|---:|
| linear_regression | 5 | 0.428163 | 0.381239-0.470460 | 0.540204 | 0.478609-0.592253 |
| persistence | 5 | 0.566021 | 0.508144-0.624679 | 0.703043 | 0.632300-0.789040 |

Sprint 1 implements only the required baselines: persistence and simple linear regression.
No generic relationship-weight mechanism, dynamic weighting, or ignore-value logic is included.

## Correctness Self-Check

The Sprint 1 test suite includes two permanent checks:

- same-seed synthetic generation writes identical CSV bytes;
- OLS on the seed `11` training split recovers the known synthetic drivers within tolerance.

For seed `11`, the fitted non-zero drivers are expected to align with the frozen generation formula:

- `driver_a_lag1` near `+0.35`;
- `driver_b_lag2` near `-0.25`;
- `target_lag1` near `+0.55`.

The observed `target_lag1` coefficient is lower than `0.55` in finite samples. This is expected because the generated signals share history, creating mild collinearity; it is not treated as a pipeline bug.
