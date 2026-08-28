# Nestor Delta Website Backend Contract

Status: Report JSON v1 implemented through W5; frozen for frontend binding.

The backend adapts existing S1-S10 outputs into JSON. Every algorithmic field
maps to an existing Delta capability; the W1 adapter may compose and serialize
these outputs, but must not redefine algorithm semantics. The frontend renders
only. It must not recompute relation weight, lag, stability, uncertainty,
lifecycle, evidence, or confidence.

Delta is a relationship lie-detector, not a prediction dashboard. It should say
"I don't know" when evidence is insufficient. A null field is a result, not a
missing UI value.

## Website API

### `POST /analyze`

Runs the existing S1-S10 pipeline on one monthly dataset and returns one Report
JSON v1. Exactly one of `case_name`, `csv_base64`, or `eurostat` must be
provided.

```json
{
  "case_name": "spain_retail_eurostat_2008_2025",
  "csv_base64": null,
  "date_column": "date",
  "target": "retail_volume",
  "candidate_signals": [
    "unemployment_rate",
    "consumer_confidence",
    "industrial_production",
    "hicp"
  ],
  "transform_declarations": {
    "retail_volume": "diff",
    "unemployment_rate": "diff",
    "consumer_confidence": "diff",
    "industrial_production": "diff",
    "hicp": "diff"
  },
  "train_end": "2023-12",
  "lag_window": 3,
  "eurostat": null
}
```

W3 may fetch Eurostat JSON-stat data, but the analysis engine still consumes an
aligned snapshot. The adapter turns Eurostat responses into a hash-bound CSV
snapshot first, then passes that snapshot into the same audit/analyze path.
The core adapter has no third-party dependency. To run the FastAPI wrapper,
install the optional `web` extra and start:

```bash
uvicorn nestor_delta_service.app:app --host 0.0.0.0 --port $PORT
```

### `POST /audit` (dry-run - declaration preview, W2)

Same request body as `/analyze`. Runs **only** intake + per-signal diagnostics +
transform-declaration validation. It does **not** call the evidence gate, compute
relations, or run S9 rolling. It lets the frontend preview the audit and catch a
bad declaration **before** Analyze.

Successful response:
`{ schema_version, outcome, snapshot, data_audit, transform_diagnostics }` with
`outcome=ok_to_analyze`. Validation failures use the shared structured error
format and may also include the audit blocks computed before rejection.

**Single source of truth:** `data_audit` and `transform_diagnostics` are produced
by one function shared with `/analyze`; for the same input both endpoints return
these two blocks byte-for-byte identically. The rejection rule is identical too:
a signal with `highly_persistent_risk` and declared `none` yields
`verdict: rejected` and a `422 high_persistence_requires_transform` on **both**
endpoints - never a silent pass.

### `POST /snapshot` (W3)

Prepares a frozen CSV snapshot without running audit or analysis. It accepts the
same request body as `/analyze`, including the Eurostat form:

```json
{
  "target": "retail_volume",
  "candidate_signals": ["industrial_production"],
  "transform_declarations": {
    "retail_volume": "diff",
    "industrial_production": "diff"
  },
  "train_end": "2023-12",
  "lag_window": 2,
  "eurostat": {
    "start": "2008-01",
    "end": "2025-12",
    "series": [
      {
        "name": "retail_volume",
        "dataset": "sts_trtu_m",
        "filters": {
          "freq": "M",
          "geo": "ES",
          "s_adj": "SCA",
          "unit": "I21"
        }
      },
      {
        "name": "industrial_production",
        "dataset": "sts_inpr_m",
        "filters": {
          "freq": "M",
          "nace_r2": "C",
          "s_adj": "SCA",
          "unit": "I15",
          "geo": "ES"
        }
      }
    ]
  }
}
```

Response:

```json
{
  "schema_version": "delta.report.v1",
  "outcome": "snapshot_ready",
  "snapshot": {
    "hash": "sha256-of-csv",
    "source": "eurostat",
    "provenance": { "source": "eurostat", "series": [] }
  },
  "csv_base64": "base64-encoded-csv",
  "columns": ["date", "retail_volume", "industrial_production"],
  "row_count": 216
}
```

The frontend may save this CSV and later call `/audit` or `/analyze` with
`csv_base64`; the hash is the boundary between mutable data intake and
reproducible analysis.

### Status Semantics

| Situation | HTTP | `outcome` |
|---|---:|---|
| Snapshot was prepared | 200 | `snapshot_ready` |
| Audit passed and analysis may run | 200 | `ok_to_analyze` |
| Pipeline ran and at least one relation selected | 200 | `ok` |
| Pipeline ran, but no relation cleared the gate | 200 | `baseline_only` |
| Bad or rejected input | 422 | `validation_error` |
| Pipeline crashed | 500 | `analysis_failure` |
| Unknown bundled case | 404 | `not_found` |

`baseline_only` is a successful result, not "No data".

## Report JSON v1

Top-level report shape:

```json
{
  "schema_version": "delta.report.v1",
  "producer": "nestor-delta",
  "pipeline_version": "s10.sha256.000000000000",
  "outcome": "ok | baseline_only | validation_error | analysis_failure | not_found",
  "generated_as_of": "2023-12",
  "case": {
    "name": "spain_retail_eurostat_2008_2025",
    "target": "retail_volume",
    "candidate_signals": ["industrial_production"],
    "frequency": "monthly",
    "n_observations": 216,
    "train_end": "2023-12",
    "lag_window": 3
  },
  "snapshot": {
    "hash": null,
    "source": "case | upload | eurostat",
    "provenance": null
  },
  "configuration": {
    "inputs": {
      "source": "case",
      "train_end": "2023-12",
      "lag_window": 3,
      "candidate_count": 4,
      "train_observations": 192,
      "transform_declarations": {}
    },
    "effect": {
      "score_scope": "full_train_window",
      "ranking": "score_descending_then_source"
    },
    "noise_floor": {
      "role": "diagnostic_not_gate",
      "comparisons": 12,
      "alpha": 0.05
    },
    "evidence_gate": {
      "selection_terms": ["FDR", "stability", "uncertainty", "sample_support"],
      "alpha": 0.05,
      "min_stability": 0.45,
      "max_uncertainty": 0.2,
      "min_sample_support": 0.5
    }
  },
  "transform_declarations": {},
  "transform_diagnostics": [
    {
      "signal": "hicp",
      "declared": "diff",
      "lag1_acf": 0.99247,
      "highly_persistent_risk": true,
      "verdict": "accepted"
    }
  ],
  "data_audit": {
    "date_axis": {
      "continuous": true,
      "expected_months": 216,
      "present": 216,
      "missing_months": [],
      "duplicate_months": []
    },
    "signals": [
      {
        "signal": "hicp",
        "sample_count": 216,
        "unit": "unknown",
        "seasonal_adjustment": "unknown",
        "coverage": { "start": "2008-01", "end": "2025-12", "months": 216 },
        "lag1_acf": 0.99247,
        "highly_persistent_risk": true
      }
    ],
    "candidate_pool_available": true
  },
  "baseline": { "name": "persistence", "mae": null },
  "evaluation": null,
  "noise_floor": {
    "sample_count": 191,
    "comparisons": 12,
    "alpha": 0.05,
    "threshold": 0.1896
  },
  "relations": [],
  "selection": {
    "fit_status": "fit | baseline_only_no_evidence",
    "final_mode": "delta | baseline_only | not_evaluated",
    "selected_count": 0,
    "selected_sources": []
  },
  "prediction_confidence": {
    "confidence": null,
    "components": {
      "relation_stability": null,
      "parameter_uncertainty": null,
      "input_support": null,
      "residual_uncertainty": null
    },
    "capped_by": null
  },
  "narrative": { "headline": "", "lines": [] },
  "warnings": []
}
```

W2 fills `data_audit` and `transform_diagnostics` in both `/audit` and
`/analyze`. For the same input, those two blocks must match byte-for-byte.
W3 fills `snapshot.hash` for case, upload, and Eurostat sources, and fills
Eurostat provenance when data is fetched through the adapter. M3 adds
`configuration` so reports publish the effective parameters and rules that can
change conclusions. `evaluation` may still be null.

## RelationView

One object per candidate relation from source to target:

```json
{
  "source": "industrial_production",
  "target": "retail_volume",
  "lag": 2,
  "transform": "diff",
  "effect": {
    "score": 0.355,
    "weight": -0.355,
    "sign": -1,
    "noise_floor": 0.1896,
    "effect_size_vs_noise_floor": 1.87
  },
  "significance": {
    "p_value": 0.0009,
    "fdr_threshold": 0.0125,
    "clears": true
  },
  "stability": 0.35,
  "uncertainty": 0.07,
  "sample_support": 1.0,
  "lifecycle": { "state": "birth", "points": null },
  "selected": false,
  "reason_code": "insufficient_stability",
  "reason_text": "Evidence is not stable enough to select.",
  "trajectory": null
}
```

`effect.score` is the absolute Pearson correlation on explicitly transformed
data, computed over the full training window for the reported best lag.
`effect.weight` is the signed version of the same estimate. S9 rolling windows
provide `stability`, `uncertainty`, and `lifecycle`; they must not replace the
full-window `effect.score`.

`noise_floor` and `effect_size_vs_noise_floor` are diagnostic calibration
fields, not an Evidence Gate threshold in v1. Selection is decided by the
FDR-corrected effect test plus stability, uncertainty, and sample-support gates.
Frontend surfaces must not render the noise-floor comparison as a pass/fail
badge.

Lifecycle labels must be displayed with the corresponding `stability` value
when they carry visual weight. A valid state such as `stable` can still hide
uneven temporal support unless the numeric stability is shown beside it.

`stability`, `uncertainty`, `selected`, confidence fields, and `trajectory` are
nullable. Null means insufficient evidence or not run in W1.

## Enumerations

- `outcome`: `snapshot_ready`, `ok_to_analyze`, `ok`, `baseline_only`,
  `validation_error`, `analysis_failure`, `not_found`
- lifecycle `state`: `birth`, `strengthening`, `stable`, `decaying`, `dead`
- evidence `reason_code`: `selected`, `below_fdr_corrected_effect`,
  `insufficient_stability`, `excess_relationship_uncertainty`,
  `insufficient_sample_support`, `not_selected`
- transform declaration: `none`, `diff`, `log_diff`
- transform verdict: `accepted`, `rejected`
- `fit_status`: `fit`, `baseline_only_no_evidence`
- `final_mode`: `delta`, `baseline_only`, `not_evaluated`

`final_mode` and lifecycle state are independent. Never merge them into one
health score.

## Selected-Relation Ledger

The selected-relation ledger is not part of Report JSON. It is an append-only
Run-boundary sidecar for completed API runs with selected relations. Each JSONL
row records `run_id`, `snapshot_hash`, `target`, `source`, relation
`lag`/`sign`/`score`/`stability`, `generated_as_of`, and `pipeline_version`.
The default path is `/tmp/nestor_delta_relationship_ledger.jsonl`; deployments
can set `NESTOR_RELATIONSHIP_LEDGER_PATH` for durable storage.

Ledger writes are fail-soft: append failures are logged but never fail the
analysis request. `/api/v1/capabilities` reports `ledger.enabled`,
`ledger.configured`, `ledger.durable`, `ledger.writable`,
`ledger.last_write_ok`, `ledger.lines`, the resolved `ledger.path`, and any
`ledger.write_probe_error`.

`ledger.durable` is now an observed current-process signal, not an environment
variable mirror. It is true only when a non-default path is configured and the
latest same-directory write observation passes. The probe is cached for 60
seconds, while real appends update the observation immediately. `ledger.lines`
is counted when a path is first observed or recovers, then incremented after
successful single-process appends, so `/health` and `/api/v1/capabilities` do
not scan the append-only file on every request. `ledger.last_write_ok` reports the most
recent real append outcome, or `null` before any selected relation has been
written to the observed path in the process. This still does not prove
cross-restart persistence: a deployment that must accumulate a durable record
has to mount a volume, set `NESTOR_RELATIONSHIP_LEDGER_PATH` to that mount, and
verify the file out of band.

## Error Format

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

Error code examples: `non_contiguous_dates`, `duplicate_month`,
`undeclared_transform`, `high_persistence_requires_transform`,
`unknown_signal`, `too_few_observations`, `singular_fit`, `case_not_found`.

## Frontend State Inventory

Every surface must distinguish:

- loading
- legal empty: `outcome=baseline_only`, HTTP 200
- populated: `outcome=ok`, HTTP 200
- validation error: HTTP 422
- analysis failure: HTTP 500
- not found: HTTP 404
- null field: explicit insufficient-evidence chip, not zero

W1 decisions:

- `prediction_confidence` is per-report only.
- `trajectory` is optional and may be `null` or `[]`.
- backend emits conservative `narrative.headline` and `narrative.lines`;
  frontend lays them out only.
