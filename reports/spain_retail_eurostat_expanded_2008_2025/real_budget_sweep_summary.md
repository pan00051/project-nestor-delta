# Real Case Budget Sweep: spain_retail_eurostat_expanded_2008_2025

Scope: a fixed five-tier pressure scan connecting S5 relation filtering to the S6 prediction path. Results describe co-movement and out-of-sample predictive usefulness only; they do not establish causality.

- Target: `retail_volume`
- Candidate signals: 12
- Rows: 216
- Train labels: 190
- Test labels: 24
- Lag window: 2
- Maximum admitted signals: 12
- Baseline comparator: persistence

## Fixed Budget Tiers

| Budget | Threshold | Candidates | After threshold | After cap | Actual OLS | MAE change vs persistence | Fit status |
|---:|---:|---:|---:|---:|---:|---:|---|
| 1.00 | 0.06 | 12 | 12 | 12 | 11 | 77.72% | `fit_after_collinearity_backoff` |
| 0.75 | 0.17 | 12 | 11 | 11 | 10 | 46.56% | `fit_after_collinearity_backoff` |
| 0.50 | 0.28 | 12 | 6 | 6 | 6 | 66.89% | `fit` |
| 0.25 | 0.39 | 12 | 4 | 4 | 4 | 30.41% | `fit` |
| 0.00 | 0.50 | 12 | 4 | 4 | 4 | 30.41% | `fit` |

## Interpretation Boundary

- All five budget tiers were fixed before evaluation. This report does not select or announce a winning tier from test results.
- Relation scoring, threshold filtering, ranking, capping, collinearity backoff, and model fitting use train rows only. All tier signal sets and coefficients are frozen before test evaluation begins.
- The `0.06` minimum threshold is a frozen S5 pressure-scan parameter derived from the synthetic benchmark. It is not a universal real-data noise cutoff.
- Trends and seasonality in real data can raise relation scores, including scores for relationships that do not generalize.
- Downstream proxies use the number admitted after the cap. They exclude upstream relation discovery, target-history features, the intercept, and measured wall-clock runtime.
- Empty Delta fields mean no Delta model was fitted for that tier; baseline values are not copied into Delta columns.

## Notes

Exploratory expansion of the frozen Eurostat Spain retail case. Eight additional monthly Spain series were fixed before this run; all cover 2008-01 through 2025-12 with no deletion, interpolation, or imputation. The 2024-2025 test period was already observed in the original case, so any improvement here is exploratory and requires a new untouched period for confirmation. Results describe co-movement and out-of-sample predictive usefulness, not causation. Clean CSV SHA-256: 38c5d92976c0769f3e75c2e04d625118214bb8c3327d8d4e850f6f58c813b01f.
