# Trust-Gating Prediction Summary

Protocol: `EVALUATION.md` v1 frozen split, five seeds, and test MAE/RMSE.

Default gate: trust `<= 0.15` is blocked, trust `>= 0.50` is fully admitted, and values between them use linear admission.
Direction is stored separately from absolute trust. Gated sources are combined before OLS so the model cannot independently undo their relative admissions.

## Prediction Comparison

| Mode | Runs | MAE mean | MAE range | RMSE mean | RMSE range |
|---|---:|---:|---:|---:|---:|
| sprint3_ols | 5 | 0.422277 | 0.375342-0.457150 | 0.532636 | 0.470656-0.589775 |
| trust_gated_ols | 5 | 0.454786 | 0.415817-0.492024 | 0.568517 | 0.518068-0.634403 |

Trade-off: trust gating has 7.70% higher mean MAE and 6.74% higher mean RMSE than the frozen Sprint 3 OLS mode.
It still beats persistence, but this experiment is about making trust numerically operative, not claiming a guaranteed accuracy gain.

## Gate Admissions

| Source | Runs | Direction | Trust mean | Trust range | Admission mean | Admission range | Blocked runs |
|---|---:|---:|---:|---:|---:|---:|---:|
| driver_a | 5 | +1 | 0.610370 | 0.586565-0.636637 | 1.000000 | 1.000000-1.000000 | 0 |
| driver_b | 5 | -1 | 0.390663 | 0.284401-0.483912 | 0.687608 | 0.384004-0.954034 | 0 |
| noise | 5 | mixed | 0.084508 | 0.058352-0.147512 | 0.000000 | 0.000000-0.000000 | 5 |

## Weight Sensitivity Check

Counterfactual: preserve every relation's direction and selected lag, change only `driver_b` trust to `1.0`, and refit on the same train samples. Noise remains blocked.

| Mode | Runs | Mean prediction delta | Per-seed range |
|---|---:|---:|---:|
| sprint3_ols | 5 | 0.0000000000 | 0.0000000000-0.0000000000 |
| trust_gated_ols | 5 | 0.0774200737 | 0.0081728375-0.1567707161 |

The Sprint 3 OLS delta is numerical roundoff: independent non-zero feature scaling is re-estimated away.
The gated delta is material because trust changes the composition of the shared relation signal before OLS; blocked information cannot be reconstructed from separate source columns.

## Boundary

This is a static, deterministic trust-gating experiment. It does not implement dynamic weights, threshold tuning, resource adaptation, or causal attribution.
