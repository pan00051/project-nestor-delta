# Real Case Budget Sweep: spain_retail_eurostat_2008_2025

Scope: a fixed five-tier pressure scan connecting S5 relation filtering to the S6 prediction path. Results describe co-movement and out-of-sample predictive usefulness only; they do not establish causality.

- Target: `retail_volume`
- Candidate signals: 4
- Rows: 216
- Train labels: 190
- Test labels: 24
- Lag window: 2
- Maximum admitted signals: 4
- Baseline comparator: persistence

## Fixed Budget Tiers

| Budget | Threshold | Candidates | After threshold | After cap | Actual OLS | MAE change vs persistence | Fit status |
|---:|---:|---:|---:|---:|---:|---:|---|
| 1.00 | 0.06 | 4 | 4 | 4 | 4 | 63.27% | `fit` |
| 0.75 | 0.17 | 4 | 4 | 4 | 4 | 63.27% | `fit` |
| 0.50 | 0.28 | 4 | 2 | 2 | 2 | -0.03% | `fit` |
| 0.25 | 0.39 | 4 | 2 | 2 | 2 | -0.03% | `fit` |
| 0.00 | 0.50 | 4 | 2 | 2 | 2 | -0.03% | `fit` |

## Observed Result

- The full four-signal tiers (`budget_ratio` 1.00 and 0.75) overfit: their test MAE is approximately 63% worse than persistence. Consumer confidence and HICP showed spurious in-sample co-movement that did not hold out of sample.
- At `budget_ratio` 0.50, 0.25, and 0.00, the higher threshold removes consumer confidence and HICP while retaining the two stronger co-moving signals, industrial production and unemployment. The resulting test MAE difference is approximately -0.03%, which is effectively level with persistence and must not be interpreted as beating the baseline.
- In this fixed, pre-frozen sweep, the ignore-threshold mechanism therefore acts as an overfitting guard: increasing pressure removes the harmful signals and moves the model from substantial out-of-sample overfit back to approximate parity with persistence. This is an observed result for this case, not a causal claim or a universally selected operating point.

## Interpretation Boundary

- All five budget tiers were fixed before evaluation. This report does not select or announce a winning tier from test results.
- Relation scoring, threshold filtering, ranking, capping, collinearity backoff, and model fitting use train rows only. All tier signal sets and coefficients are frozen before test evaluation begins.
- The `0.06` minimum threshold is a frozen S5 pressure-scan parameter derived from the synthetic benchmark. It is not a universal real-data noise cutoff.
- Trends and seasonality in real data can raise relation scores, including scores for relationships that do not generalize.
- Downstream proxies use the number admitted after the cap. They exclude upstream relation discovery, target-history features, the intercept, and measured wall-clock runtime.
- Empty Delta fields mean no Delta model was fitted for that tier; baseline values are not copied into Delta columns.

## Notes

Eurostat Spain monthly snapshot for 2008-01 through 2025-12. Target is seasonally and calendar adjusted retail sales volume (G47, 2021=100). Candidate signals are seasonally adjusted unemployment, seasonally adjusted consumer confidence, seasonally and calendar adjusted industrial production (2021=100), and the all-items HICP index (2025=100). An external Case Builder enforced the exact 216-month axis with no missing rows, deletion, interpolation, or imputation; clean CSV SHA-256 is a8c01df041db4d835baf83a459ae65194a4d5c9bca157753d56cd6259d106445. Eurostat marked the retail and industrial source snapshots provisional. Results are co-movement and out-of-sample predictive usefulness only.
