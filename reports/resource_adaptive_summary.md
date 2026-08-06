# Sprint 5 Resource-Adaptive Ignore Summary

Protocol: deterministic five-budget scan over two tracks. The S4 frozen drift data is used as a correctness regression; the new high-dimensional fixture is used only for resource stress.

`BENCHMARK_NOISE_FLOOR = 0.06` is the observed benchmark floor from the current frozen synthetic setup with max-over-lag relation scoring. It is not a universal statistical threshold for real data.

Threshold rule: `threshold = MIN_THRESHOLD + (1 - budget_ratio) * (MAX_THRESHOLD - MIN_THRESHOLD)`, with `MAX_PRESSURE_THRESHOLD = 0.50`.

Resource metrics are downstream proxies after relation discovery. They do not claim end-to-end compute reduction because all candidate relations are still scored before ignoring.

## resource_stress

| Budget ratio | Threshold | Retained relations mean | Retained range | Downstream compute reduction mean | Downstream memory reduction mean | MAE mean | MAE loss mean | RMSE mean | RMSE loss mean | Tier retention mean |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1.00 | 0.06 | 13.20 | 12-15 | 0.00% | 0.00% | 0.500765 | 0.00% | 0.627749 | 0.00% | S 3.0 / M 4.0 / W 3.6 / N 2.6 |
| 0.75 | 0.17 | 7.60 | 7-9 | 41.56% | 41.56% | 0.517833 | 4.11% | 0.636626 | 1.99% | S 3.0 / M 3.6 / W 1.0 / N 0.0 |
| 0.50 | 0.28 | 3.60 | 3-5 | 73.00% | 73.00% | 0.769678 | 55.23% | 0.945561 | 52.20% | S 3.0 / M 0.6 / W 0.0 / N 0.0 |
| 0.25 | 0.39 | 2.00 | 1-3 | 84.49% | 84.49% | 0.899831 | 81.77% | 1.140325 | 83.34% | S 2.0 / M 0.0 / W 0.0 / N 0.0 |
| 0.00 | 0.50 | 0.20 | 0-1 | 98.46% | 98.46% | 1.172330 | 137.57% | 1.473365 | 137.42% | S 0.2 / M 0.0 / W 0.0 / N 0.0 |

## s4_correctness_regression

| Budget ratio | Threshold | Retained relations mean | Retained range | Downstream compute reduction mean | Downstream memory reduction mean | MAE mean | MAE loss mean | RMSE mean | RMSE loss mean | Tier retention mean |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1.00 | 0.06 | 2.40 | 2-3 | 0.00% | 0.00% | 0.546983 | 0.00% | 0.683606 | 0.00% | S 1.0 / M 1.0 / W 0.0 / N 0.4 |
| 0.75 | 0.17 | 2.00 | 2-2 | 13.33% | 13.33% | 0.547689 | 0.14% | 0.683878 | 0.05% | S 1.0 / M 1.0 / W 0.0 / N 0.0 |
| 0.50 | 0.28 | 1.80 | 1-2 | 23.33% | 23.33% | 0.557901 | 2.03% | 0.696852 | 2.00% | S 0.8 / M 1.0 / W 0.0 / N 0.0 |
| 0.25 | 0.39 | 0.80 | 0-1 | 66.67% | 66.67% | 0.594630 | 8.74% | 0.738947 | 8.09% | S 0.0 / M 0.8 / W 0.0 / N 0.0 |
| 0.00 | 0.50 | 0.00 | 0-0 | 100.00% | 100.00% | 0.619695 | 13.32% | 0.770477 | 12.75% | S 0.0 / M 0.0 / W 0.0 / N 0.0 |

## Acceptance Notes

- As `budget_ratio` falls, threshold rises monotonically by construction.
- Retained relation counts and downstream proxies are expected to be monotonic non-increasing within each seed because the same train-only weight ranking is filtered by higher thresholds.
- The full per-seed retention table is tracked in `reports/resource_adaptive_retention.csv`.
- Actual wall-clock time is intentionally not an acceptance metric because local machine load is not byte-reproducible.
