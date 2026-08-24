# Nestor — Insight ⇄ Delta Integration Boundary (v1)

**Status:** v1 draft · agreed scope, not yet implemented.
**Relationship to `WEBSITE_CONTRACT_W0.md`:** W0 remains the single source of truth for the
**analysis contract** (Report JSON v1 schema, S1–S10 field mapping, outcome semantics,
frontend IA). This document does **not** replace or restate it. It governs only the
**product-to-product boundary**: resource shape, the Report/Run split, and how v1 is allowed
to evolve. Where the two documents overlap, W0 wins.

**Scope — three concerns only:**

1. API resource shape (§2)
2. Report vs Run boundary (§3)
3. v1 evolution policy + contract-test requirements (§4)

Consumer-side obligations are in §5. Everything explicitly out of scope is in §6.

---

## 0. Governing principles

**P1 — Delta does not know Insight exists.**
Delta exposes a stable capability surface. It must never contain a branch keyed on the
calling product. `X-Nestor-Client` may be recorded in logs and echoed in the Run envelope;
it must never reach analysis code or change a result. Any per-caller behaviour belongs in
Insight, not in Delta.

**P2 — Report is a pure function; Run is an execution record.**

```
report = f(snapshot_id, analysis_params, effective_configuration, pipeline_version)
```

Nothing outside that tuple may affect a single byte of `report`. Same snapshot,
same params, same effective configuration, same version → byte-identical report,
on any machine, at any wall-clock time. This is the product's credibility claim
(Delta is a relationship lie-detector), and it is what makes `snapshot.hash`
meaningful.

**P3 — `baseline_only` is a success.**
HTTP `200`, `outcome: "baseline_only"`. It is the product's signature state, not an error
and not "no data". No error code may ever be minted for it. (W0 §1.)

**P4 — Additive-only within v1.** See §4.

---

## 1. Version identifiers — three distinct things

| Identifier | Lives in | Changes when | Example |
|---|---|---|---|
| `api_version` | URL path + Run envelope | transport/resource shape changes | `v1` |
| `schema_version` | Report body | Report JSON schema changes | `delta.report.v1` **(frozen — do not rename)** |
| `pipeline_version` | Report body | S1–S10 analysis code changes | `s10.2026.08.1` |

`pipeline_version` is the field that explains "same data, different result". It is part of the
reproducibility triple (P2) and therefore belongs in the Report, alongside
`producer: "nestor-delta"`.

`schema_version` keeps its already-frozen literal `"delta.report.v1"`. It is asserted by the
existing test suite; renaming it is a breaking change with no benefit.

---

## 2. API resource shape

### 2.1 Endpoints

```
POST /api/v1/runs            # submit an analysis
GET  /api/v1/runs/{run_id}   # retrieve a submitted analysis
GET  /api/v1/capabilities    # what this Delta instance supports
```

`POST /analyze` is retained as an unversioned alias of `POST /api/v1/runs` for the existing
frontend. New consumers use the versioned paths only.

Request body for `POST /api/v1/runs` is unchanged from W0 §1.

### 2.2 Response envelope

```jsonc
{
  "run": {
    "run_id": "01J...",            // UUID/ULID, server-generated
    "report_id": "01J...",         // UUID/ULID, null while status != "completed"
    "status": "completed",         // see 2.3
    "api_version": "v1",
    "created_at": "2026-08-23T09:14:02Z",   // wall clock — the ONLY wall clock in the response
    "completed_at": "2026-08-23T09:14:05Z",
    "duration_ms": 3120,
    "client": "nestor-insight",    // echo of X-Nestor-Client; log/telemetry only
    "requested_by": null,          // reserved for auth
    "tenant_id": null              // reserved for auth
  },
  "report": { "schema_version": "delta.report.v1", "...": "W0 §2" }
}
```

`report` is `null` unless `run.status == "completed"`.

### 2.3 Run status enum (frozen)

`pending` · `running` · `completed` · `failed`

`run.status` describes **execution**; `report.outcome` describes the **analysis result**.
They are independent: a `completed` run legitimately carries `outcome: "baseline_only"`.
Never collapse them into one field.

### 2.4 Execution mode — resource shape now, queue later

`POST /api/v1/runs` executes **synchronously** in v1 and returns `200` with
`status: "completed"` and the report inline. No job queue, no worker, no state machine is
built now.

If analysis later becomes slow, `POST` starts returning `202` with `status: "pending"` and a
`null` report. **The URL shape and the client contract do not change** — which is the entire
point of adopting this shape early. See the consumer obligation in §5.1; without it the
migration is still breaking.

### 2.5 HTTP status mapping

| Situation | HTTP | Envelope |
|---|---|---|
| Ran, ≥1 relation selected | `200` | full envelope, `outcome: "ok"` |
| Ran, legal empty | `200` | full envelope, `outcome: "baseline_only"` |
| Input rejected — **no run is created** | `422` | W0 §6 error body, **no `run` object** |
| Unknown case | `404` | W0 §6 error body, no `run` object |
| Pipeline crashed — run exists | `500` | `run.status: "failed"` + W0 §6 `error` |

Rule: **validation happens before a Run resource exists.** A request that never became a run
gets no `run_id`. A run that started and crashed keeps its `run_id` and is retrievable.

Error bodies keep the W0 §6 shape — including `schema_version` and `outcome` — so a consumer
parses success and failure with one reader.

### 2.6 Run retention — state this honestly

There is no persistence layer yet. v1 implements a **bounded in-process store** (recent runs
only, lost on restart) so `GET /api/v1/runs/{run_id}` is real rather than a permanent `404`.

`/api/v1/capabilities` must advertise this:

```jsonc
"run_retention": { "mode": "in_memory_process_lifetime", "max_runs": 100 }
```

Insight must not treat a run as durable until capabilities says otherwise. Shipping a GET
endpoint that silently always 404s is worse than not shipping it.

### 2.7 Idempotency

Because `snapshot_id` is content-addressed (§3.2), the reproducibility triple
`(snapshot_id, analysis_params, pipeline_version)` is a natural idempotency key. A repeat
submission of an identical triple **may** return the existing run instead of recomputing.
Optional in v1; the key must exist regardless.

### 2.8 `GET /api/v1/capabilities`

Unauthenticated, cheap, cacheable. Minimum contents:

```jsonc
{
  "api_version": "v1",
  "report_schema_version": "delta.report.v1",
  "pipeline_version": "s10.2026.08.1",
  "inputs": { "bundled_cases": ["..."], "csv_upload": true, "max_upload_bytes": 5242880 },
  "eurostat": { "enabled": true, "presets": ["ei_bssi_m_r2"], "dataset_search": false },
  "execution": { "mode": "sync" },
  "run_retention": { "mode": "in_memory_process_lifetime", "max_runs": 100 },
  "ledger": { "enabled": true, "durable": true, "path": "/data/relationship_ledger.jsonl" },
  "features": { "pdf_export": false, "report_persistence": false, "sharing": false }
}
```

This is how Insight learns which Eurostat presets exist without hardcoding them, and how it
learns the day `execution.mode` flips to `"async"`.

### 2.9 Auth entry point

Delta accepts `Authorization: Bearer <token>` through a **single auth dependency stub** that
allows all requests in local/dev. No OAuth, no user model, no token issuance in v1. The
requirement is only that endpoints are not designed such that they can only be driven by the
local UI, and that there is exactly one place to implement enforcement later.

`X-Nestor-Client: <name>` is recorded, never branched on (P1).

---

## 3. Report vs Run boundary

### 3.1 Field placement

| Field | Home | Why |
|---|---|---|
| `schema_version`, `producer`, `pipeline_version` | Report | part of the reproducibility triple |
| `configuration` | Report | effective parameter values and the rules that selected them |
| `generated_as_of` | Report | **data date** of the past-only boundary — not wall clock |
| `snapshot.hash`, `snapshot.source`, `snapshot.provenance` | Report | describes the input |
| analysis params (`target`, `candidate_signals`, `transform_declarations`, `train_end`, `max_lag`) | Report (`case`) | inputs to `f` |
| all S1–S10 outputs, `data_audit`, `narrative`, `warnings` | Report | outputs of `f` |
| `run_id`, `report_id`, `status`, `api_version` | Run | execution identity |
| `created_at`, `completed_at`, `duration_ms` | Run | wall clock, non-reproducible |
| `client`, `requested_by`, `tenant_id` | Run | caller identity, mutable, unenforced |

**Never in the Report:** wall-clock timestamps, caller identity, tenancy, auth subjects, run
IDs, request headers. Two concrete reasons: (a) they break byte-identical reproducibility and
therefore break any future signing/hashing of the report; (b) an always-`null` `tenant_id`
inside the report is indistinguishable from "no tenancy" and invites consumers to trust a
field nothing enforces.

`created_at` (Run, wall clock) and `generated_as_of` (Report, data date) must never appear
side by side. Keeping them in different objects is the structural guard against the
look-ahead bug this distinction exists to prevent.

### 3.2 Snapshot identity

`snapshot_id` **is** the existing SHA-256 of (data + manifest) — not a fresh UUID.
Content-addressing gives: identical input → identical id on any machine at any time;
free idempotency (§2.7); and a stable cross-product handle for "the same data".

`run_id` and `report_id` are opaque server-generated UUID/ULIDs, since they identify events,
not content.

### 3.3 No duplicated truth

The snapshot hash appears exactly once, at `report.snapshot.hash`. It is not mirrored to a
top-level `input_snapshot_sha256`. Two locations for one value is two things to keep in sync.

---

## 4. v1 evolution policy and contract tests

### 4.1 Additive-only

Within `delta.report.v1` and `/api/v1`, **permitted**:

- adding a new optional field
- adding a new value to an open enum (see 4.2)
- adding a new endpoint

**Breaking — requires v2:** removing a field · renaming a field · changing a field's type ·
changing a field's meaning · making an optional field required · removing an enum value ·
changing HTTP status semantics.

`null` keeps its W0 meaning throughout: **"insufficient evidence"**, never `0`, never "missing".

### 4.2 Enum handling — the one rule that prevents silent breakage

Adding an enum value is additive **for Delta** and breaking **for a strict consumer**.
Therefore: **consumers must tolerate unknown enum values** — degrade to a neutral rendering,
log, and continue; never crash, never map an unknown value onto a known one.

This applies to: `outcome` · `run.status` · `lifecycle.state` · `reason_code` ·
`transform.declared` · `transform.verdict` · `fit_status` · `final_mode` · error `code`.

Closed enums (never extended in v1): `outcome`, `fit_status`, `final_mode`, `run.status`.
Open enums (will grow): `reason_code`, error `code`, `lifecycle.state`.

### 4.3 Schema as an executable artifact

The contract is maintained by CI, not by prose. Documents drift; tests do not.

- Pydantic models are the source; JSON Schema is generated from them and committed.
- The generated schema plus `mock_reports_v1.json` are published as a versioned shared
  artifact that **both** repos consume.
- **Delta CI:** every response validates against the committed schema; a schema diff that is
  not additive fails the build.
- **Insight CI:** parses every fixture in `mock_reports_v1.json` — which must cover `ok`,
  `baseline_only`, `validation_error`, `analysis_failure` — plus a fixture containing a
  deliberately unknown enum value and an unknown extra field, asserting neither breaks the
  reader (4.2).

A schema change that lands without regenerating the shared artifact is the failure mode this
section exists to prevent.

---

## 5. Consumer obligations (Insight side)

**5.1 Poll-shaped from day one.** Insight reads `run.status` first. If `completed`, it uses
the inline `report`. Otherwise it polls `GET /api/v1/runs/{run_id}`. It must implement this
**while Delta is still synchronous** — code that assumes an inline report is exactly what the
§2.4 migration would break.

**5.2 `baseline_only` is a result to render, not an error to handle.** It must reach the same
success path as `ok`, with different presentation. (P3, W0 §8.)

**5.3 Never merge `final_mode` with `lifecycle.state`.** `final_mode` answers "should I trust
Delta at all" (S8 guard); `lifecycle.state` answers "is this one relation alive" (S9). They
are independent signals and must not be combined into a single health score or status chip.
(W0 §4.)

**5.4 No derived-status fields are provided.** Delta does not emit convenience booleans such
as `forecast_available`, and Insight must not expect them. Derive from the source fields
(`selection.selected_count > 0`); a materialised derived field is a second truth that drifts.

**5.5 Read `selected_count`, not `len(relations)`.** `relations[]` contains **every candidate**,
selected or not (W0 §3). Counting the array is not counting the selected relations.

**5.6 Discover, don't hardcode.** Eurostat presets, bundled cases, upload limits and feature
flags come from `/api/v1/capabilities`.

---

## 6. Explicitly out of scope for this document

Deferred by decision, not by oversight:

- **Job queue / worker / async execution** — shape reserved (§2.4), implementation deferred
  until there is measured need.
- **Sub-resource endpoints** (`/runs/{id}/audit`, `/transforms`, `/evidence`) — the Report is
  the atomic unit; fetching parts separately risks serving pieces from different runs. If
  payload size becomes a real problem, add `GET /api/v1/reports/{id}?include=audit,transforms`
  rather than independent resources.
- **Durable persistence, accounts, tenancy enforcement, share links, PDF export, public
  deployment** — no fields or endpoints are being designed for these beyond the reserved
  `requested_by` / `tenant_id` slots in the Run envelope and the auth stub in §2.9.
- **Generic Eurostat dataset search / indicator catalogue** — not implemented; capabilities
  reports `dataset_search: false`.
- Anything governed by `WEBSITE_CONTRACT_W0.md`.
