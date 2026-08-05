# Sprint 2 Relation Weight Validation

Protocol: layer-independent lagged Pearson relation weights over the five frozen synthetic seeds.

Rows summarize source variables ranked for target `target`. Ranges are min-max.

| Source | Runs | Mean rank | Rank range | Mean score | Score range |
|---|---:|---:|---:|---:|---:|
| driver_a | 5 | 1.00 | 1-1 | 0.595528 | 0.548573-0.663159 |
| driver_b | 5 | 2.00 | 2-2 | 0.393421 | 0.331254-0.464283 |
| noise | 5 | 3.00 | 3-3 | 0.059127 | 0.020952-0.093188 |

Acceptance check: known drivers `driver_a` and `driver_b` should rank ahead of `noise` for `target` across the frozen seeds.
This script validates the standalone weighting mechanism only; it does not run weighted prediction.
