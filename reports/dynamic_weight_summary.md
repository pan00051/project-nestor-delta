# Sprint 4 Dynamic Weight Summary

Protocol: additive frozen S4 drift protocol in `EVALUATION.md`; five independent seeds and a 120-row causal rolling window.

The frozen OLS coefficients and source selection use train labels only. At test step `t`, dynamic relation weights use rows `t-120` through `t-1`; after prediction, row `t` becomes available only to later steps.

## Known-Drift Tracking

`truth` is the generative lag-1 coefficient. `static weight` and `dynamic weight` are marginal Pearson relation weights, so direction and movement are compared rather than coefficient equality.

| Seed | Truth start | Truth end | Static weight | Dynamic start | Dynamic end | Dynamic change | Correct direction |
|---:|---:|---:|---:|---:|---:|---:|:---:|
| 101 | 0.401397 | 0.650000 | 0.301321 | 0.593029 | 0.687364 | +0.094336 | yes |
| 103 | 0.401397 | 0.650000 | 0.297572 | 0.582205 | 0.684493 | +0.102288 | yes |
| 107 | 0.401397 | 0.650000 | 0.351062 | 0.656903 | 0.695980 | +0.039077 | yes |
| 109 | 0.401397 | 0.650000 | 0.277157 | 0.454736 | 0.583780 | +0.129045 | yes |
| 113 | 0.401397 | 0.650000 | 0.292233 | 0.373927 | 0.637194 | +0.263266 | yes |

Tracking acceptance: 5/5 seeds move in the known positive drift direction from test start to test end.
The complete test-step truth/static/dynamic trajectory is in `reports/dynamic_weight_trajectory.csv`.

## Prediction Comparison

| Mode | Runs | MAE mean | MAE range | RMSE mean | RMSE range |
|---|---:|---:|---:|---:|---:|
| dynamic_weights | 5 | 0.506484 | 0.463798-0.572600 | 0.640280 | 0.580674-0.715281 |
| static_weights | 5 | 0.547689 | 0.490096-0.624914 | 0.683878 | 0.636739-0.768990 |

Dynamic weights reduce mean MAE by 7.52% and mean RMSE by 6.38% versus static weights on the frozen drift test.

## Boundary

This is deterministic rolling adaptation of Sprint 2 relation weights. It does not tune the window, refit OLS after training, implement ignore-value resource adaptation, or modify S0-S3.1 logic and data.
