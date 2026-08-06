# Trust-Gating Prediction Mode

> Status: Sprint 4 static trust-gating implementation note.

## Purpose

Trust gating makes the numerical magnitude of Sprint 2 relation weights affect prediction before OLS is fitted. It is an additional prediction mode; the frozen Sprint 3 workflow remains unchanged.

The module is deterministic, standard-library only, and static. It does not implement dynamic weights.

## Interface

The layer-independent gate is in `src/nestor_delta/trust_gating.py`:

```python
linear_admission(trust, config)
build_trust_gates(weights, target, config)
combine_gated_signals(row, gates)
```

The prediction composition is in `src/nestor_delta/trust_gated_prediction.py`:

```python
fit_prediction_mode(rows, train_label_rows, mode="ols")
fit_prediction_mode(rows, train_label_rows, mode="trust_gated")
predict_with_mode(rows, label_rows, model, mode)
```

`mode="ols"` delegates to the unchanged Sprint 3 implementation. `mode="trust_gated"` uses the new pre-OLS gate.

## Gate Rule

Trust is the absolute relation score `abs(weight)`. Direction is stored separately as `sign(weight)`.

The default piecewise-linear admission is:

```text
admission(s) = 0                              when s <= 0.15
admission(s) = (s - 0.15) / (0.50 - 0.15)   when 0.15 < s < 0.50
admission(s) = 1                              when s >= 0.50
```

The two thresholds are explicit configuration values. They are fixed for the reported experiment and are not tuned on validation or test metrics.

The default ignore threshold `0.15` is just above the largest train-only noise score observed across the five frozen seeds (`0.147512`). This blocks all five noise relations. The weakest real driver remains admitted with coefficient `0.384004`, so the rule distinguishes weak signal from the observed noise floor rather than treating every non-dominant source as absent.

## Why the Gate Is Before OLS

Multiplying each independent OLS feature column by a non-zero constant does not make that weight operative. Unconstrained OLS can divide its fitted coefficient by the same constant and recover the same prediction.

The gated mode therefore does two things before fitting:

1. It applies `direction * admission` to each source.
2. It combines all admitted sources into one shared relation signal for each lag.

For lag `k`:

```text
gated_signal[t-k] = sum(direction_j * admission_j * source_j[t-k])
```

OLS receives lagged target history and these shared gated signals. It may fit the overall coefficient of each shared signal, but it cannot separately amplify a discounted source or reconstruct a blocked source because the individual source columns are not present.

This is the smallest linear, interpretable constraint that makes relative trust identifiable while preserving OLS as the final fitting method.

## Verification

Run:

```bash
python scripts/run_trust_gating.py
python -m unittest discover -s tests
```

Tracked outputs:

- `reports/trust_gating_metrics.csv`
- `reports/trust_gating_admissions.csv`
- `reports/trust_gating_sensitivity.csv`
- `reports/trust_gating_summary.md`

The sensitivity experiment preserves direction and selected lag, changes only weak-source `driver_b` trust to `1.0`, and then refits on the same train samples. Noise remains blocked. Across five seeds, the frozen Sprint 3 OLS mode changes only by floating-point roundoff, while gated predictions have a mean absolute change of `0.0774200737` (range `0.0081728375-0.1567707161`).

## Boundary

This module does not:

- modify Sprint 1, 2, or 3 logic;
- tune thresholds against test performance;
- update weights over time;
- implement resource-aware threshold adjustment;
- claim causal interpretation or algorithmic novelty.
