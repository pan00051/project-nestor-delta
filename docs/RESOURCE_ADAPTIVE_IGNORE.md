# Sprint 5 Resource-Adaptive Ignore

Sprint 5 turns the existing ignore/gating idea into a downstream resource adaptation mechanism.

It does not reimplement Sprint 3.1 trust gating. It reuses the same basic idea that low-trust relations can be blocked, but changes the control input: a fixed ignore threshold becomes a deterministic threshold schedule driven by `budget_ratio`.

## Interface

The layer-independent module is `src/nestor_delta/resource_adaptive_ignore.py`.

Inputs:

- relation weights from the frozen Sprint 2 mechanism;
- a target variable name;
- `budget_ratio` in `[0.0, 1.0]`;
- frozen threshold bounds.

Outputs:

- adaptive threshold;
- retained target relations;
- downstream compute and memory proxy estimates.

It does not compute relation weights itself, fit prediction models, read machine CPU or memory state, or claim upstream relation-discovery savings.

## Threshold Schedule

Frozen constants:

```text
BENCHMARK_NOISE_FLOOR = 0.06
MAX_PRESSURE_THRESHOLD = 0.50
```

Rule:

```text
threshold = BENCHMARK_NOISE_FLOOR
            + (1.0 - budget_ratio)
            * (MAX_PRESSURE_THRESHOLD - BENCHMARK_NOISE_FLOOR)
```

`budget_ratio = 1.00` maps to threshold `0.06`. `budget_ratio = 0.00` maps to threshold `0.50`.

The `0.06` value is a benchmark noise floor from the frozen synthetic setup and the max-over-lag Pearson scoring rule. It is not a universal real-world statistical cutoff.

## Resource Boundary

S5 currently filters after relation discovery, so the metrics are explicitly downstream proxies:

```text
downstream_compute_proxy =
    retained_relation_count
    * downstream_lag_count
    * effective_row_count

downstream_memory_proxy =
    retained_feature_count
    * materialized_lag_count
    * effective_row_count
```

`estimated_memory_bytes` multiplies the memory proxy by `bytes_per_value`.

Reduction is measured against the full-budget `budget_ratio = 1.00` result within the same seed and track.

## Two Tracks

`s4_correctness_regression` uses the frozen S4 drift data. It checks that the adaptive threshold is deterministic, train-only, and does not break existing low-dimensional behavior.

`resource_stress` uses a new high-dimensional fixture with 15 candidate sources: 3 strong, 4 medium, 4 weak, and 4 noise sources. This track demonstrates the resource/quality tradeoff curve.

Reports:

- `reports/resource_adaptive_metrics.csv`
- `reports/resource_adaptive_retention.csv`
- `reports/resource_adaptive_summary.md`

Entry point:

```bash
python scripts/run_resource_adaptive_ignore.py
```
