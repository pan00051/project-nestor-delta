# Sprint 2 Relation Weighting Mechanism

> Status: Sprint 2 implementation note.

## Purpose

The relation weighting module is the first reusable capability in Nestor Delta.

It estimates how strongly one numeric signal relates to another over recent history. The first implementation uses lagged Pearson correlation and chooses the strongest absolute correlation over a fixed lag search window.

This is an engineering baseline for a reusable mechanism, not a claim of algorithmic novelty.

## Interface

Module:

```text
src/nestor_delta/relation_weights.py
```

Primary function:

```python
compute_lagged_relation_weights(rows, variables, max_lag)
```

Inputs:

- `rows`: ordered records such as `{"target": 1.0, "driver_a": 0.2}`.
- `variables`: variable names to compare.
- `max_lag`: maximum positive lag to search.

Output:

- A list of `RelationWeight` records.
- Each record describes one directed `source -> target` relation.
- Fields: `source`, `target`, `lag`, `weight`, `score`, `sample_count`.

Interpretation:

- `weight` is signed Pearson correlation at the selected lag.
- `score` is `abs(weight)` and is used for ranking relation strength.
- `lag` is the lag that produced the strongest absolute correlation.

## Statistical Interpretation Notes

The Sprint 2 weight is a marginal pairwise correlation, not a partial or controlled effect.

This means it should not be compared one-to-one with Sprint 1 OLS coefficients. For example, the synthetic data can produce a `driver_a -> target` relation weight near `0.60`, while the frozen generation formula uses a direct coefficient of `0.35`. That is expected: pairwise correlation includes shared history and indirect paths, while an OLS coefficient estimates a net effect after other features are included.

For the same reason, `weight` should be read as a signed relation score for ranking and feature construction, not as a causal coefficient or final prediction coefficient.

The current implementation searches multiple lags and keeps the largest absolute correlation. This creates a small multiple-comparison bias: a pure noise variable will often receive a non-zero best score because one of the searched lags is randomly strongest. In the Sprint 2 validation report, `noise` has a mean score near `0.06` rather than exactly `0.00`. That does not affect the current ranking because the real drivers are well separated, but it matters for any future ignore-value threshold: a useful threshold must sit above the observed noise floor, not merely above zero.

## What It Does Not Do

The module does not:

- predict future values;
- know which variable is a business target;
- tune model hyperparameters;
- decide which weak signals to ignore;
- track dynamic changes over time;
- explain causality or event impact;
- depend on Nestor Insight or any other Nestor layer.

Those boundaries keep this capability layer-independent and reusable.

## Validation Standard

Sprint 2 validation is intentionally minimal:

- unit tests must show deterministic output and correct ranking on a tiny known dataset;
- `scripts/run_weights.py` must run across the five frozen synthetic seeds;
- on the frozen synthetic data, known drivers `driver_a` and `driver_b` should rank ahead of `noise` for target `target`;
- results must be saved in `reports/weight_validation.csv` and `reports/weight_validation_summary.md`.

The validation does not need to beat forecasting baselines; that belongs to Sprint 3.
