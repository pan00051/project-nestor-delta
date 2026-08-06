# Dynamic Relation Weights

Sprint 4 adds a layer-independent causal wrapper around the frozen Sprint 2 relation-weight function. The wrapper repeatedly feeds a fixed-width historical window into the existing static function; it does not alter that function.

## Capability Interface

`compute_rolling_relation_weights(rows, variables, max_lag, steps, window_size)` accepts:

- named numeric histories;
- candidate variable names and the existing maximum lag;
- the time steps at which weights are required;
- one deterministic window size.

It returns `TimedRelationWeight` records containing the effective step, exclusive window bounds, source, target, selected lag, signed Pearson weight, absolute score, and sample count.

For step `t`, the wrapper slices `rows[max(0, t-window_size):t]`. Its output therefore cannot inspect row `t` or the future. The module has no knowledge of train/test splits, prediction, synthetic truth, business semantics, or resource budgets.

## Frozen S4 Choice

The S4 benchmark freezes a 120-row sliding window. This gives each Pearson estimate substantially more observations than the five-lag search while remaining shorter than the 180-row coefficient drift. It is a fixed protocol choice, not a tuned model parameter.

The benchmark uses the original static Pearson weights as follows:

1. Select the top two sources from train rows only.
2. Fit static and dynamic OLS models on the same train labels `120-419`.
3. Combine the selected signed source weights into one shared relation signal per input lag.
4. Keep OLS fixed after training; update only the dynamic relation weights.
5. At test step `t`, use rows through `t-1`, then reveal row `t` only for later predictions.

The shared signal follows the established S3.1 rationale: independent source columns would let unconstrained OLS cancel non-zero weight scaling. S4 uses raw signed relation weights and introduces no S5 ignore-value or resource-adaptive behavior.

## Interpretation

The frozen truth is a generative regression coefficient, while Sprint 2 outputs a marginal Pearson correlation. Their absolute values are not expected to match. S4 validates whether the dynamic Pearson weight moves in the known drift direction and whether that adaptation improves prediction relative to the same weight held static.

Run:

```bash
python scripts/run_dynamic_weights.py
```

Tracked outputs:

- `reports/dynamic_weight_metrics.csv`
- `reports/dynamic_weight_trajectory.csv`
- `reports/dynamic_weight_tracking.csv`
- `reports/dynamic_weight_summary.md`

Generated drift data and truth sidecars live under `data/synthetic_drift/` and remain reproducible, untracked artifacts, matching the original synthetic-data policy.
