# Real Case Budget Sweep: frozen_real_budget_sweep_acceptance

Scope: a fixed five-tier pressure scan connecting S5 relation filtering to the S6 prediction path. Results describe co-movement and out-of-sample predictive usefulness only; they do not establish causality.

- Target: `target`
- Candidate signals: 15
- Rows: 216
- Train labels: 187
- Test labels: 24
- Lag window: 5
- Maximum admitted signals: 5
- Baseline comparator: persistence

## Fixed Budget Tiers

| Budget | Threshold | Candidates | After threshold | After cap | Actual OLS | MAE change vs persistence | Fit status |
|---:|---:|---:|---:|---:|---:|---:|---|
| 1.00 | 0.06 | 15 | 15 | 5 | 5 | -42.52% | `fit` |
| 0.75 | 0.17 | 15 | 5 | 5 | 5 | -42.52% | `fit` |
| 0.50 | 0.28 | 15 | 4 | 4 | 4 | -34.34% | `fit` |
| 0.25 | 0.39 | 15 | 2 | 2 | 2 | -26.16% | `fit` |
| 0.00 | 0.50 | 15 | 0 | 0 | 0 | n/a | `baseline_only_no_retained_signal` |

## Interpretation Boundary

- All five budget tiers were fixed before evaluation. This report does not select or announce a winning tier from test results.
- Relation scoring, threshold filtering, ranking, capping, collinearity backoff, and model fitting use train rows only. All tier signal sets and coefficients are frozen before test evaluation begins.
- The `0.06` minimum threshold is a frozen S5 pressure-scan parameter derived from the synthetic benchmark. It is not a universal real-data noise cutoff.
- Trends and seasonality in real data can raise relation scores, including scores for relationships that do not generalize.
- Downstream proxies use the number admitted after the cap. They exclude upstream relation discovery, target-history features, the intercept, and measured wall-clock runtime.
- Empty Delta fields mean no Delta model was fitted for that tier; baseline values are not copied into Delta columns.

## Notes

Synthetic acceptance fixture derived mechanically from the first 216 rows of frozen S5 resource_stress_seed_227.csv; not a real-world result.
