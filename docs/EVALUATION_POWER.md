# S8 · Evaluation Power

> **Status:** implemented, awaiting author acceptance and cross-review with S7.
> **Scope rule:** additive only. No existing module, report, or protocol was modified.

## 1. The problem this Sprint fixes

The frozen Sprint 0/1 protocol evaluates on **one** chronological test window. On the
Spain retail case that window holds 24 monthly observations, and persistence MAE is
`0.8042` -- exactly the mean absolute monthly change, because persistence on a level
series is a forecast of zero change.

With 24 points the standard error of the MAE skill ratio is roughly **20 percent**.
Every effect S9 and S10 hope to detect is smaller than that. The protocol cannot
distinguish a real improvement from sampling noise, and a single number gives no way
to see the problem.

This has already produced a claim the data does not support. The dual-window findings
report a validation gain of `7.11%` and a pandemic-window loss of `9.63%`, and read
that reversal as evidence of a structural break. At this sample size the two figures
are not statistically distinguishable from each other. The break may well be real; the
current protocol simply cannot be the thing that establishes it.

## 2. What was added

| Module | Answers |
|---|---|
| `rolling_origin.py` | Evaluate at many forecast origins instead of one. |
| `interval_metrics.py` | MASE, directional accuracy, worst-decile error, change-space error, and bootstrap intervals over folds. |
| `noise_floor.py` | How large must `\|r\|` be, at this `n`, before it is distinguishable from luck? |

### 2.1 Rolling origin

`build_rolling_origin_folds` turns an ordered sequence of label rows into successive
past-only folds. The Spain retail case goes from **1 test window to 93 folds**. Every
fold is checked by `assert_folds_are_past_only`, which raises if a fold trains on a row
at or after its own origin. Fold construction is deterministic and depends only on its
arguments; the frozen single split is recoverable as the `max_folds=1` special case.

### 2.2 Interval reporting

`skill_interval` reports the per-fold skill distribution: median, a deterministic
bootstrap interval, and every individual fold value. `excludes_zero` states whether the
result resolves at all. A fixed seed makes the interval byte-reproducible.

**A result is now a range, and a range that spans zero is reported as unresolved rather
than as a number.**

### 2.3 Metrics the single split could not support

- **MASE** -- scaled by the in-sample naive change, so it is independent of the series
  level and comparable across cases.
- **Directional accuracy** -- reports `decided` separately from `accuracy`. Persistence
  forecasts zero change at every step, so its `decided` share is `0%`: the metric makes
  that explicit instead of scoring a flat forecast as if it had an opinion.
- **Worst-decile error** -- the tail an average hides.
- **Change-space error** -- an error of `0.80` on a level near `108` reads as `0.74%`
  and looks small. It is `100%` of the typical monthly move. This reports errors on the
  scale where the forecast actually operates.

### 2.4 Noise floor

`correlation_noise_floor(n, comparisons)` returns the `|r|` a score must exceed to be
distinguishable from chance, using the Fisher z transform with a Sidak correction for
multiple comparisons.

| `n` | comparisons | threshold |
|---|---|---|
| 191 | 1 | `0.1420` |
| 191 | 6 (a lag 1-6 scan) | `0.1896` |
| 24 | 1 | `0.4034` |

The frozen Sprint 5 constant `BENCHMARK_NOISE_FLOOR = 0.06` does not depend on `n` and
sits **below** the floor at every case size in this repository.

**`s5_config.py` is not modified and Sprint 5 behaviour is unchanged.** This module only
supplies the measurement. Replacing the constant belongs to the S10 Evidence Gate.

Selecting a lag by `argmax |r|` over a scan is itself a multiple comparison, so the
reported score is biased upward by the selection. `lag_scan_noise_floor` gives the
corrected threshold for that procedure.

## 3. Acceptance

Run: `python scripts/run_evaluation_power.py`
Artifacts: `reports/evaluation_power/` (a new directory; no existing report is touched).

### 3.1 Harness controls

An evaluation harness must be shown incapable of manufacturing signal before any result
it produces can be believed. Three controls, each aimed at a different failure mode:

| Control | Construction | Requirement | Result |
|---|---|---|---|
| sign_flip_null | the model's own per-fold skill with signs randomized (mean-aggregated) | interval must contain zero (zero-centred by construction) | **pass** (both cases) |
| identity | persistence scored against itself | every fold exactly zero | **pass** (both cases) |
| scrambled | model refit on signals whose time order is destroyed | interval must not reach above zero | **pass** (both cases) |
| degraded | persistence plus a shock the size of a typical move | interval must sit entirely below zero | **pass** (both cases) |

> **Recorded spec error.** The first version of this suite had a single control -- an
> "uninformed random predictor" -- required to produce an interval *containing* zero.
> It failed on the first run at `-29.5%`, correctly: adding noise to persistence is
> strictly worse than persistence, so negative skill was the right answer and the
> requirement was wrong. The one control was doing three jobs badly. It was split into
> the three above. The error is recorded rather than quietly corrected, because a
> harness whose own acceptance criteria were never wrong has probably not been tested.

### 3.2 Single split versus rolling origin (stand-in model)

| Case | Single-split skill | Test points | Folds | Rolling median | 90% interval | Resolves? |
|---|---|---|---|---|---|---|
| `spain_retail_eurostat_2008_2025` | `-1037.29%` | 24 | 93 | `-515.69%` | `[-615.88%, -338.49%]` | yes |
| `spain_industrial_shock_2008_2021` | `-60.63%` | 24 | 46 | `-24.79%` | `[-64.38%, +17.21%]` | **no** |

The second row is the finding. A single split reported a confident-looking `-60.63%`
drawn from a distribution whose 90% interval reaches `+17.21%`. **A number that
decisive came from evidence that cannot even settle the sign.**

The first row is the necessary counterpart: when a model is reliably bad, the interval
says so and stays far from zero. The protocol is not simply refusing to conclude
anything -- it resolves large effects and declines to resolve small ones.

## 4. Known limitations

1. **The stand-in harness is a demonstration only — the faithful recheck now exists.**
   `run_evaluation_power.py` uses a plain lagged OLS and its numbers **must not be read
   as the published result**; its report is renamed `harness_demonstration.md` to make
   that explicit. The faithful re-evaluation of the published `+7.11% / -9.63%` result,
   using the frozen selection and baseline guard, is `run_dual_window_recheck.py`
   (see section 7).
2. **Bootstrap over folds assumes fold errors are exchangeable.** Overlapping expanding
   windows share training data, so the interval is somewhat optimistic. A block
   bootstrap would be tighter and is deferred.
3. **Relation scoring still runs on non-stationary levels.** That is S7's scope. Until
   S7 lands, these intervals measure the honesty of the evaluation, not the validity of
   the relations being evaluated.

## 5. Interface boundary with S7

S7 and S8 were built in parallel and must not collide:

| Concern | Owner | Operates on |
|---|---|---|
| series to series transforms for **relation scoring** | S7 `stationarity.py` | a whole column |
| error decomposition in **change space for evaluation** | S8 `interval_metrics.py` | `(previous_actual, actual, prediction)` triples |

`interval_metrics.change_space_errors` differences *forecasts and outcomes* to score
them. It never transforms an input series and does not import from S7. The two Sprints
share no module, no constant, and no output path.

## 6. Handoff

- [x] Route `real_case_analysis.py` through `build_rolling_origin_folds` so published
      case results carry intervals. Frozen single-split reports stay as protocol v1.
- [x] Restate the dual-window `+7.11% / -9.63%` conclusion using the real pipeline under
      rolling origin, and amend `DUAL_WINDOW_FINDINGS.md` with whatever comes back.
- [ ] S10 consumes `noise_floor` to replace the fixed `0.06` in the Evidence Gate.


## 7. Dual-window recheck (faithful, frozen selection)

`run_dual_window_recheck.py` re-evaluates the published Case B result without
re-selecting: the frozen selected source set and lag from `validation_selection.json`
are held fixed, and only the OLS coefficients are refit on each origin's past-only
window. The fit/predict path is reused verbatim from `real_case_analysis.py`, so the
model is the published model, not a stand-in. (OLS is invariant to constant per-source
weight scaling, so frozen sources enter with weight 1.0 with no effect on predictions.)

**Faithfulness check.** The refit reproduces the published validation-era block skill
exactly at `+7.11%`; the pandemic block reproduces at `-7.10%` versus the published
`-9.63%`. The residual gap is a recorded artifact discrepancy: `validation_selection.json`
lists the fifth source as `domestic_energy_producer_prices` while
`frozen_test_summary.md` lists `construction_confidence`. The JSON (machine artifact) is
used as the source of truth and the discrepancy is flagged, not silently resolved.

**Semantic guard.** The `-9.63%` is a single regime (the 2020-2021 pandemic). Rolling
origins across the ordinary span do **not** put an error bar on it. They give the frozen
model's ordinary-period skill distribution; the pandemic block is placed as its own
segment against that distribution. The two are reported separately and never merged.

**Finding (partially corrects, partially supports the original Finding 2).**

| Era | Origins | Per-origin median skill | 90% interval | Resolves? |
|---|---|---|---|---|
| validation | 24 | `+11.46%` | `[-8.05%, +40.62%]` | no |
| pandemic | 24 | `-46.73%` | `[-75.72%, -7.57%]` | yes |

- The published `+7.11%` validation **gain is within per-origin noise** — its interval
  spans zero, so it is not a resolvable improvement over persistence. This corrects the
  implicit reading that validation showed a real edge.
- The pandemic **degradation is resolvable**: the interval sits entirely below zero and
  the pandemic median falls **outside** the validation-era band. This **supports** the
  original Finding 2's structural-break reading — but now on the actual frozen model,
  with an interval, rather than on one number.

Output: `reports/evaluation_power/dual_window_recheck.md` and
`dual_window_recheck_real.csv`.
