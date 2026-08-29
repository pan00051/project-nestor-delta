# M0 — Ground-truth evidence calibration

> **What these fixtures are — and are not.** `s_gt_1_positive` is a **calibration positive
> control**: a synthetic dataset with a relationship deliberately injected so the detector's
> response to a *known* answer can be measured. It is **not** a real-world causal finding, and
> `true_driver` does not "cause" anything outside this file. Delta detects statistical
> relationships that survive its evidence tests; it does not establish causation. Any use of
> this fixture in a demo must present it as what it is — a ground-truth check on the
> instrument, not evidence about the world. That framing is also the stronger claim.

Drop-in bundle for `DEMO_MILESTONES_V1.md` M0. Answers one question before any UI,
deployment or API work is worth doing: **does the evidence gate select when it should and
refuse when it should?**

```
tests/
  generate_ground_truth.py     run once; commit the output (re-runs are guarded)
  test_ground_truth.py         S-GT-0/1/2/2b/3
  measure_sensitivity.py       S-GT-4 — a measurement, not a pass/fail test
  fixtures/
    s_gt_1_positive.csv        sha256 823ffad1…  216 months, injected relation
    s_gt_2_negative.csv        sha256 e10234e8…  216 months, pure noise
    manifest.json              seeds, request payloads, data diagnostics, hashes
```

## Wiring it in — one function

`run_report()` in `test_ground_truth.py` is the only repo-specific code:

```python
from nestor_delta.api import analyze     # TODO: real entrypoint
return analyze(payload)
```

Everything else asserts against `Report JSON v1`, so the controls survive refactors of
S1–S10. Setting `NESTOR_API_BASE=http://localhost:8000` runs the identical suite through
`POST /api/v1/runs`, which makes it double as an M1 check that the API returns what
in-process execution returns.

## Fixture design

Series are designed in the **differenced** domain and integrated into levels, so a user
uploads levels and declares `diff`, and the pipeline recovers exactly the stationary series
designed here. This exercises the real upload path rather than a synthetic shortcut, and it
makes the levels genuinely persistent (lag-1 ACF ≈ 0.98), so the S7 persistence guard is
exercised passing rather than firing.

**S-GT-1** — `true_driver` leads `synthetic_target` by **2 months** with a **negative** sign
at |r| ≈ 0.59, alongside **three independent decoys**. The decoys matter: the same run must
select the real driver *and* reject three fakes, which is what exercises FDR correction.
Lag 2 is interior to the lag window on purpose — a lag pinned at the boundary is a weaker test.
Sign is negative on purpose: a detector that reports the right magnitude with an inverted sign
passes every strength check while telling the user the opposite of the truth.

**S-GT-2** — same shape, no relationship anywhere. Required, not optional: a detector that
selects nothing and one that selects everything both pass S-GT-1.

### Seeds are screened — and that is deliberate

The screen is applied to properties of the **data** (maximum spurious lagged correlation
< 0.13), **never to the pipeline's output**. Screening on data properties is fixture
specification; screening on pipeline output would be rigging the test.

It is necessary because at n = 215 the standard error of a sample correlation is ≈ 0.068, so
across 4 signals × 4 lags an unscreened "pure noise" draw routinely throws a spurious
|r| ≈ 0.20 — above the noise floor the contract's own example uses (0.1896). The first seed
tried here did exactly that. Such a seed makes the negative control fail while the pipeline is
behaving correctly. A deterministic CI control must be unambiguous; the statistical question
is answered by **S-GT-2b**, which measures the false-positive rate across 20 unscreened seeds.

## Reading the results

| Outcome | Meaning | Action |
|---|---|---|
| S-GT-1 ✅ S-GT-2 ✅ | gate is directionally sound | proceed; record the M0 decision |
| **S-GT-1 ❌** | gate mis-calibrated for differenced monthly series | **stop downstream work** — a bug, and the most valuable find in the cycle |
| S-GT-2 ❌ | gate admits spurious relations | worse than a miss: the product's entire claim is refusal |
| S-GT-3 ❌ | same input → different report | `snapshot.hash` means nothing; fix before anything else |

## S-GT-4 — the measurement that explains `baseline_only`

```
python generate_ground_truth.py --sweep     # 只写 sweep 文件，不动已冻结的控制组
python measure_sensitivity.py
```

Re-running the generator will **not** overwrite `s_gt_1_positive.csv` or
`s_gt_2_negative.csv` once they exist — numpy's Generator stream and pandas' CSV float
formatting are not guaranteed identical across versions, so an incidental regeneration on a
different machine can move the ground truth while S-GT-0 still passes (the manifest is
rewritten alongside it). `--force` regenerates deliberately; nothing else does.

Sweeps injected |r| from 0.15 to 0.60 and reports where the gate starts selecting. That number
is the detector's **sensitivity floor** at n = 216, lag ≤ 3 — and it converts the open question
"why does `ei_bssi_m_r2` return `baseline_only`?" into a fact:

- floor ≈ 0.25–0.35 → the gate is reasonable and real monthly differenced macro relations simply
  sit below it. `baseline_only` on real data is **explained**, and the floor becomes a number
  worth quoting to an audience.
- floor ≈ 0.8+ → nothing real will ever clear the gate. That is a bug, and it costs days here
  instead of surfacing mid-demo.

It is also how the M0 threshold rule is enforced rather than argued: **any gate threshold change
must move the positive and negative controls in the same direction**, with before/after recorded.

## If no real dataset ever selects

`DEMO_MILESTONES_V1.md` M0 branch (b) — promote S-GT-1 to the demo's positive case. Worth noting
that this may be the **better** demo regardless: an audience watching Delta pick `true_driver`
out of a field containing `decoy_1/2/3`, and say why each decoy was rejected, understands the
product in about ten seconds. An obscure macro pair does not read that way. It is honest —
the data is labelled synthetic, and "here is our detector against known ground truth" is a
stronger claim than a single cherry-picked real correlation.

## Q6 — rolling-window boundary controls

The adapter switches from the no-rolling S9 path to the rolling lifecycle path
when `train_observations > lag_window + 8` (`src/nestor_delta_service/adapter.py`,
`_s9_relation_objects`, `_lifecycle_block`, and `_trajectory_block`). With the
ground-truth default `lag_window = 3`, the last non-rolling train size is 11.
Once rolling is active, its effective window is:

```
min(36, max(lag_window + 6, train_observations // 3))
```

Q6 adds two fixed controls derived from that rule:

| Fixture | Train n | Side | Expected |
|---|---:|---|---|
| `s_gt_6_pre_rolling_negative.csv` | 11 | no rolling (`effective_window: null`) | `baseline_only`, `selected_count: 0` |
| `s_gt_6_rolling_positive.csv` | 51 | rolling (`effective_window: 17`) | selects `true_driver`, lag 2, sign −1 |
| `s_gt_6_rolling_negative.csv` | 51 | rolling (`effective_window: 17`) | `baseline_only`, `selected_count: 0` |

The positive control uses the first prefix of the accepted S-GT-1 seed that
both enters the rolling path and gives the unchanged Evidence Gate enough
trajectory evidence to select the injected relation. The reported
`effect.score` remains the full training-window transformed correlation:
`0.6230268430213287` for Q6 positive. The final rolling point is
`0.6323873577775484`; it may feed stability/lifecycle only and must not replace
the headline effect score.

Q6.1 adds the missing rolling-side negative control. Its top reported relation
is `noise_3` with full-window `effect.score = 0.26227702663262514`, while that
same relation's final rolling point is `0.464238688557278`. All four noise
sources still return `selected: false`, preserving the refusal side of the
instrument inside the rolling branch.
