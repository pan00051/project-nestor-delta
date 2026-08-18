# Rolling-Origin Harness Demonstration (stand-in model)

This report uses a plain lagged-OLS **stand-in** model, not the published
Delta pipeline. It demonstrates why a single split hides uncertainty and how
the guards behave. It is **not** the dual-window recheck: the faithful
re-evaluation of the published `+7.11% / -9.63%` result, using the frozen
selection and baseline guard, is produced by `run_dual_window_recheck.py`.

## Single split versus rolling origin (stand-in model)

| Case | Single-split skill | Test points | Rolling folds | Rolling median | 90% interval | Resolves? |
|---|---|---|---|---|---|---|
| `spain_retail_eurostat_2008_2025` | -1037.29% | 24 | 93 | -515.69% | [-615.88%, -338.49%] | yes |
| `spain_industrial_shock_2008_2021` | -60.63% | 24 | 46 | -24.79% | [-64.38%, +17.21%] | no |

These numbers describe the stand-in model only. A single split reports one
number drawn from the rolling interval and gives no way to see its width.

## Harness controls

See `harness_controls.csv`. Four guards, each aimed at a distinct failure
mode:

- **sign_flip_null** -- the model's own per-fold skill with signs randomized.
  Centred on zero by construction, so its interval contains zero: this is the
  correct realization of the original *random-predictor-must-contain-zero*
  acceptance item. The observed skill is judged against this band.
- **identity** -- persistence scored against itself; every fold exactly zero.
- **scrambled** -- model refit on time-scrambled signals; interval must not
  reach above zero.
- **degraded** -- persistence plus a typical-size shock; interval must sit
  entirely below zero. Note: a naive noisy predictor is *not* a zero-centred
  null, it is this degraded control.

## Extended metrics

See `metrics_extended.csv` for MASE, directional accuracy, worst-decile, and
change-space error for the stand-in model across all rolling folds.
