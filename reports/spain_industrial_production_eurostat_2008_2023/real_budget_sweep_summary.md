# Real Case Budget Sweep: spain_industrial_production_eurostat_2008_2023

Scope: a fixed five-tier pressure scan connecting S5 relation filtering to the S6 prediction path. Results describe co-movement and out-of-sample predictive usefulness only; they do not establish causality.

- Target: `industrial_production`
- Candidate signals: 4
- Rows: 192
- Train labels: 165
- Test labels: 24
- Lag window: 3
- Maximum admitted signals: 3
- Baseline comparator: persistence

## Fixed Budget Tiers

| Budget | Threshold | Candidates | After threshold | After cap | Actual OLS | MAE change vs persistence | Fit status |
|---:|---:|---:|---:|---:|---:|---:|---|
| 1.00 | 0.06 | 4 | 4 | 3 | 3 | 215.90% | `fit` |
| 0.75 | 0.17 | 4 | 3 | 3 | 3 | 215.90% | `fit` |
| 0.50 | 0.28 | 4 | 1 | 1 | 1 | 225.09% | `fit` |
| 0.25 | 0.39 | 4 | 0 | 0 | 0 | n/a | `baseline_only_no_retained_signal` |
| 0.00 | 0.50 | 4 | 0 | 0 | 0 | n/a | `baseline_only_no_retained_signal` |

## Interpretation Boundary

- All five budget tiers were fixed before evaluation. This report does not select or announce a winning tier from test results.
- Relation scoring, threshold filtering, ranking, capping, collinearity backoff, and model fitting use train rows only. All tier signal sets and coefficients are frozen before test evaluation begins.
- The `0.06` minimum threshold is a frozen S5 pressure-scan parameter derived from the synthetic benchmark. It is not a universal real-data noise cutoff.
- Trends and seasonality in real data can raise relation scores, including scores for relationships that do not generalize.
- Downstream proxies use the number admitted after the cap. They exclude upstream relation discovery, target-history features, the intercept, and measured wall-clock runtime.
- Empty Delta fields mean no Delta model was fitted for that tier; baseline values are not copied into Delta columns.

## Notes

Eurostat Spain monthly manufacturing case, 2008-01 through 2023-12, with an exact 192-month axis and no deletion, interpolation, or imputation. The original request used unavailable or obsolete codes for four candidate scopes. The actual scopes and semantic differences are recorded in methodology.md and source_manifest.json. In particular, order_book_assessment is a qualitative survey balance, not the requested quantitative industrial new-orders index. Results describe co-movement and out-of-sample predictive usefulness only, not causation. Clean CSV SHA-256: ce541159b3aa8a8eeb4c3bcfe34b09e1b5e0717b8b0537ad9f48a1ec67db30da.
