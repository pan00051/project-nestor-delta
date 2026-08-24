# Nestor Delta — Website Contract (Sprint W0)

**Status:** v1 · semantic source of truth for backend field mapping + frontend design;
Pydantic and the committed JSON Schema govern machine shape and nullability.
**Amendment log:** 2026-08-24 (doc repair) — the product-framing paragraph no longer lists the
noise floor as a test relationships must survive (decision B, recorded in the M0 acceptance
record); §2 gains the three report-root fields that ship today; §3 states the noise-floor role
and the lifecycle/stability pairing rule. No schema field was removed, renamed, or retyped.
**Rule that governs everything:** the backend **adapts existing S1–S10 outputs into JSON**.
Every **algorithmic** field maps to an existing S1–S10 capability; the W1 adapter may
compose and serialize these outputs, but must not redefine algorithm semantics. It does
not invent new algorithm fields or recompute anything. The frontend **renders only** — it never recomputes
relation weight, lag, stability, uncertainty, lifecycle, evidence, or confidence.

Product framing (for anyone new to this): Delta is a **relationship lie-detector**, not a
prediction dashboard. Its job is to say whether an apparent relationship survives the
stationarity guard, the FDR-corrected effect test, and the stability, uncertainty, and
sample-support gates — and to **say "I don't know" when the evidence is insufficient**. A
blank where a number could be is a *result*, not a gap.

> The noise floor is **not** in that list. It is a diagnostic comparison scale and gates
> nothing in v1 (§3). Any sentence or screen that presents it as a threshold is claiming a
> selection rule the product does not implement.

---

## 1. API surface (W1 scope)

### `POST /analyze`
Runs the frozen S1–S10 pipeline on one already-aligned monthly dataset and returns one
`Report JSON v1`.

**Request**
```json
{
  "case_name": "spain_retail_eurostat_2008_2025",   // optional: a bundled demo case
  "csv_base64": "<...>",                             // optional: uploaded aligned CSV
  "date_column": "date",              // required for csv_base64; default "date"
  "target": "retail_volume",
  "candidate_signals": ["unemployment_rate","consumer_confidence","industrial_production","hicp"],
  "transform_declarations": {                        // required per signal + target
    "retail_volume":"diff","unemployment_rate":"diff",
    "consumer_confidence":"diff","industrial_production":"diff","hicp":"diff"
  },
  "train_end": "2023-12",
  "lag_window": 3                     // frontend may label this "Max lag"
}
```
Exactly one of `case_name` / `csv_base64` is provided. The runner does **not** fetch APIs
or clean data (that is W2/W3); it consumes an aligned snapshot only.

> Since M1 this request is also served by `POST /api/v1/runs`, which wraps the same Report in
> a Run envelope. `POST /analyze` is the retained unversioned alias. The request body is
> identical; the envelope and status semantics are governed by `API_BOUNDARY_V1.md` §2.

### HTTP status semantics — the critical rule
| Situation | HTTP | `outcome` |
|---|---|---|
| Pipeline ran, ≥1 relation selected | `200` | `ok` |
| Pipeline ran, **legal empty** — nothing cleared the gate / baseline guard fired | `200` | `baseline_only` |
| Bad/rejected input (missing months, undeclared transform, high-persistence + `none`) | `422` | `validation_error` |
| Pipeline crashed (singular fit, internal error) | `500` | `analysis_failure` |
| Unknown case | `404` | `not_found` |

> **`baseline_only` is a 200 success, not an error and not "no data".** This is the
> product's signature state. The frontend must never render it as a failure.

---

## 2. Report JSON v1 — schema

Every block is annotated with the S-sprint that produces it, so the adapter is a 1:1 map.

```jsonc
{
  "schema_version": "delta.report.v1",
  "producer": "nestor-delta",            // M3; identifies the emitting product
  "pipeline_version": "s10.sha256.3665b88553ad",  // M2; content-derived, never hand-written
  "outcome": "ok | baseline_only | validation_error | analysis_failure",
  "generated_as_of": "2023-12",          // data date of the past-only boundary, NOT wall clock
  "case": {                              // echoes request + S1 config
    "name": "spain_retail_eurostat_2008_2025",
    "target": "retail_volume",
    "candidate_signals": ["..."],
    "frequency": "monthly",
    "n_observations": 216,
    "train_end": "2023-12",
    "max_lag": 3
  },
  "snapshot": {                          // W3 fills this; v1 may be null
    "hash": null,                        // sha256 of (data + manifest) once staging exists
    "source": "case | upload | eurostat",
    "provenance": null                   // {dataset_code,filters,unit,s_adj,geo,pulled_at,provisional}
  },
  "configuration": {                     // M3; effective parameters + the rules that chose them
    "inputs": { "source":"case", "train_end":"2023-12", "lag_window":3,
                "candidate_count":4, "train_observations":192,
                "transform_declarations":{} },
    "effect": { "score_scope":"full_train_window",
                "ranking":"score_descending_then_source" },
    "noise_floor": { "role":"diagnostic_not_gate", "comparisons":12, "alpha":0.05 },
    "evidence_gate": { "selection_terms":["FDR","stability","uncertainty","sample_support"],
                       "alpha":0.05, "min_stability":0.45,
                       "max_uncertainty":0.2, "min_sample_support":0.5 }
  },

  "transform_declarations": { "retail_volume":"diff", "...":"..." },   // S7
  "transform_diagnostics": [             // S7 stationarity.signal_diagnostics
    { "signal":"hicp", "declared":"diff", "lag1_acf":0.992,
      "highly_persistent_risk": true, "verdict":"accepted" }
    // verdict: "accepted" | "rejected"  (rejected = high persistence + declared "none")
  ],
  "data_audit": null,                    // W2 fills; v1 null. Shape in §5.

  "baseline": {                          // S1 — ALWAYS present, every report
    "name": "persistence",
    "mae": 0.8042
  },
  "evaluation": {                        // S8 rolling-origin; null if not run
    "rolling_origin": {
      "folds": 93, "median": -0.05, "low": -0.12, "high": 0.03,
      "resolves": false                  // = interval excludes zero
    },
    "mase": null, "directional_accuracy": null, "worst_decile_error": null
  },
  "noise_floor": { "sample_count":191, "comparisons":12, "alpha":0.05, "threshold":0.1896 }, // S8 — diagnostic scale; gates nothing (§3)

  "relations": [ /* RelationView[] — EVERY candidate, selected or not. See §3 */ ],

  "selection": {                         // S10 EvidenceGateResult
    "fit_status": "fit | baseline_only_no_evidence",
    "final_mode": "delta | baseline_only | not_evaluated",  // S8 guard; SEPARATE signal; generic upload = not_evaluated
    "selected_count": 0,
    "selected_sources": []
  },

  "prediction_confidence": {             // S10 PredictionConfidence; nullable
    "confidence": null,                  // 0..1 or null
    "components": {
      "relation_stability": null, "parameter_uncertainty": null,
      "input_support": null, "residual_uncertainty": null
    },
    "capped_by": null                    // e.g. "input_support" when OOD vetoes — S10 fix
  },

  "narrative": {                         // W4 templated honest text; W1 may send headline only
    "headline": "No reliable relation selected — baseline active.",
    "lines": [
      "0 of 4 candidates cleared the evidence gate.",
      "Delta defers to persistence rather than fit a model it cannot defend out-of-sample."
    ]
  },
  "warnings": [ { "code":"provisional_source", "message":"Eurostat marked retail provisional." } ]
}
```

---

## 3. `RelationView` — one per candidate (selected or not)

The frontend renders the map, detail timeline, and evidence panel entirely from these.
`stability`, `uncertainty`, `selected`, and every confidence field are **nullable** — null
means "insufficient evidence", which the UI shows explicitly, never as 0.

Two cross-cutting rules govern how these fields may be displayed:

- **`noise_floor` is diagnostic, never a gate.** Selection is FDR + stability + uncertainty +
  sample support. `effect.noise_floor` and `effect_size_vs_noise_floor` are a comparison
  scale for reading effect size, and no surface may render either as a threshold, as a floor
  beneath a score, or as a pass/fail badge.
- **A lifecycle label never appears alone.** Wherever `lifecycle.state` carries visual weight
  it is shown together with the relation's `stability` value. A valid state such as `stable`
  can still hide uneven temporal support, and the numeric stability is the evidence that
  distinguishes the two.

```jsonc
{
  "source": "industrial_production",
  "target": "retail_volume",
  "lag": 2,                               // S2 argmax lag
  "transform": "diff",                    // S7
  "effect": {
    "score": 0.355,                       // |transformed r| over the full training window
    "weight": -0.355,                     // signed
    "sign": -1,
    "noise_floor": 0.1896,                // S8, comparisons-corrected — diagnostic only
    "effect_size_vs_noise_floor": 1.87    // score / noise_floor — diagnostic only
  },
  "significance": { "p_value": 0.0009, "fdr_threshold": 0.0125, "clears": true },  // S10 BH
  "stability": 0.35,                      // S9 | null
  "uncertainty": 0.07,                    // S9 | null
  "sample_support": 1.0,                  // S10 (0..1)
  "lifecycle": { "state": "birth", "points": 12 },   // S9 state machine
  "selected": false,                      // S10 evidence gate
  "reason_code": "insufficient_stability",// enum, §4
  "reason_text": "Real and above the noise floor, but stability 0.35 < 0.45.",
  "trajectory": [                         // S9 rolling; optional in v1, needed for detail timeline
    { "step": 168, "date": "2022-01", "score": 0.41, "sign": -1, "lag": 2 }
  ]
}
```

`p_value` may be arbitrarily small but is never exactly `0`. The pipeline floors it, and the
UI displays anything below `1e-12` as `< 1e-12` rather than as a rounded zero.

---

## 4. Enumerations — the values UI styles and copy key off

**`outcome`**: `ok` · `baseline_only` · `validation_error` · `analysis_failure` · `not_found`
**lifecycle `state`** (S9): `birth` · `strengthening` · `stable` · `decaying` · `dead`
**evidence `reason_code`** (S10 EvidenceDecision.reason):
`selected` · `below_fdr_corrected_effect` · `insufficient_stability` ·
`excess_relationship_uncertainty` · `insufficient_sample_support` · `not_selected`
**transform `declared`** (S7): `none` · `diff` · `log_diff`
**transform `verdict`** (S7): `accepted` · `rejected`
**`fit_status`** (S10): `fit` · `baseline_only_no_evidence`
**`final_mode`** (S8 guard): `delta` · `baseline_only` · `not_evaluated`  (generic `/analyze` upload → `not_evaluated`; only dual-window cases evaluate the guard)

> `final_mode` (should I trust Delta at all — S8 validation guard) and `lifecycle.state`
> (is this one relation alive — S9) are **two independent signals**. Never merge them into a
> single "health" number; keep them as separate Executive answers.

`lifecycle.state` and `reason_code` are **open** enums under `API_BOUNDARY_V1.md` §4.2: they
may gain values within v1, and every consumer must tolerate an unknown value by degrading to a
neutral rendering rather than crashing or mapping it onto a known state. `outcome`,
`fit_status` and `final_mode` are closed.

---

## 5. `data_audit` shape (W2 — defined now so the frontend can pre-build the page)

```jsonc
"data_audit": {
  "date_axis": { "continuous": true, "expected_months": 216, "present": 216,
                 "missing_months": [], "duplicate_months": [] },
  "signals": [
    { "signal":"hicp", "sample_count":216, "unit":"index_2015=100",
      "seasonal_adjustment":"none", "coverage":"2008-01..2025-12",
      "lag1_acf":0.992, "highly_persistent_risk":true }
  ],
  "candidate_pool_available": true
}
```
Rule (S7): a signal with `highly_persistent_risk: true` and declared `none` **must** produce
`outcome: validation_error` — never silently analyzed.

---

## 6. Error format (422 / 500 / 404)

```json
{
  "schema_version": "delta.report.v1",
  "outcome": "validation_error",
  "error": {
    "code": "non_contiguous_dates",
    "message": "Month 2019-07 is missing; the runner does not interpolate.",
    "field": "csv_base64",
    "detail": { "missing_months": ["2019-07"] }
  }
}
```
Error `code` examples: `non_contiguous_dates` · `duplicate_month` · `undeclared_transform` ·
`high_persistence_requires_transform` · `unknown_signal` · `too_few_observations` ·
`singular_fit` (500) · `case_not_found` (404).

---

## 7. Frontend information architecture (Claude's W0 half)

Landing = **Executive Summary** (the three honest answers). A persistent context bar
(case · as-of · snapshot hash when present) sits above every view.

```
Input (upload / pick case / [W3] Eurostat fetch)
   → Data Audit  (continuity, gaps, sample size, s_adj, ACF red flags)
   → Transform Declaration  (system flags, user chooses — never auto)
   → [Analyze]
   → REPORT
        ├─ Executive Summary   (3 answers; reads selection + final_mode + lifecycle)
        ├─ Relationship Map     (nodes=vars, arrows=relations; width=effect, opacity=confidence, color=lifecycle)
        ├─ Relation Detail      (one relation: badge + one-line verdict, trajectory, uncertainty band, noise floor, transform+lag)
        └─ Evidence & Confidence(gate table + confidence components + capped_by + baseline always shown)
```

Map honesty rules: dead/decaying use gray / dashed / fade — **not** red alarm. Confidence
encodes to opacity, and null confidence is a distinct "unknown" texture, never full-opacity.

> M3 recorded a sequencing decision against this IA: at the current scale (one target, four
> candidates) the ranked **evidence table** is the primary report view and the relationship
> map is secondary. The map remains a required view; it is not the hero until candidate counts
> grow. Rationale in `M3_VISUAL_AUDIT_SPEC.md`.

## 8. State inventory — every surface must define all of these

| State | Trigger | UI intent |
|---|---|---|
| loading | request in flight | skeleton, never blank |
| **legal empty** | `outcome: baseline_only` (200) | first-class result: "baseline active", explain why |
| populated | `outcome: ok` | render relations/map/detail |
| validation error | `422` | show which input is wrong + how to fix; **never** "no data" |
| analysis failure | `500` | apologize, offer retry; not the user's fault |
| not found | `404` | unknown case |
| null field | any nullable = null | explicit "insufficient evidence" chip, not 0 |

The single most important distinction: **legal empty (200 baseline_only) ≠ validation error
(422) ≠ empty screen.** Three different UIs.

---

## 9. What W0 hands to each side

- **To the new Codex window:** §1–§6. Implement `POST /analyze` as an adapter over the
  frozen pipeline; emit exactly these fields; add tests for each `outcome` + each error
  `code`; do NOT touch S1–S10 logic or invent fields.
- **To frontend design:** §7–§8 + the four mock reports (separate file
  `mock_reports_v1.json`). Build structure + design system now; bind to fields once the
  backend returns v1.
- **Open items — RESOLVED for W1:**
  - `prediction_confidence`: **per-report only** in W1 (per-relation stability/uncertainty/reason already suffice). Not per-relation.
  - `trajectory`: **optional in W1, may be `[]` or `null`**; full rolling detail lands in W2/W3.
  - `narrative`: **backend** emits a conservative templated `headline` + `lines`; the **frontend only lays them out**, never composes its own conclusion.
