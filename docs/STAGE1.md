# Sprint 3 Stage 1 Prediction

> Status: Sprint 3 implementation note.

## Purpose

Stage 1 is the first end-to-end M1 workflow: use the generic Sprint 2 relation weights to support one-step-ahead prediction of `target`.

The goal is not to invent a new model. The goal is to show that the reusable weighting mechanism can be composed with the Sprint 1 baseline machinery and produce a measurable improvement under the frozen M0 protocol.

## Workflow

For each frozen seed:

1. Generate the synthetic multivariate time series from `EVALUATION.md`.
2. Compute Sprint 2 relation weights on train rows only.
3. Rank sources for `target` and select the top two non-target variables.
4. Build a three-variable predictor using:
   - lagged `target`;
   - lagged selected source 1, scaled by its signed relation weight;
   - lagged selected source 2, scaled by its signed relation weight.
5. Fit deterministic OLS on train supervised samples.
6. Evaluate on the locked test split.

## Boundary

Stage 1 does not:

- modify the Sprint 2 weighting mechanism;
- use validation or test rows to choose weights;
- tune dynamic weights;
- introduce ignore values;
- perform causal or event attribution.

## Outputs

- `reports/stage1_metrics.csv`
- `reports/stage1_selected_sources.csv`
- `reports/stage1_summary.md`

## Current Result

Across the five frozen seeds:

| Method | MAE mean | MAE range | RMSE mean | RMSE range |
|---|---:|---:|---:|---:|
| stage1_weighted_three_variable | 0.422277 | 0.375342-0.457150 | 0.532636 | 0.470656-0.589775 |
| linear_regression | 0.428163 | 0.381239-0.470460 | 0.540204 | 0.478609-0.592253 |
| persistence | 0.566021 | 0.508144-0.624679 | 0.703043 | 0.632300-0.789040 |

Stage 1 improves mean MAE by `25.40%` against persistence and `1.37%` against the Sprint 1 linear regression baseline. The lift over linear regression is modest and should be described honestly.

## Acceptance Standard

The Stage 1 workflow should beat the Sprint 1 baselines on mean MAE and RMSE across the five frozen seeds.

If it beats persistence but not full linear regression, that must be reported honestly and Sprint 3 should not be stretched into dynamic weighting or ignore-value logic.
