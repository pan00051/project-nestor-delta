# Nestor — Insight ⇄ Delta Integration Boundary (v1)

**Status:** v1 · partly implemented. The §2 endpoints and the §3 Report/Run split are live as
of M2. §4.3 is **partly** live: Pydantic models generate a committed JSON Schema and the Delta
side validates against it, but the dual-repo shared artifact, the build-blocking non-additive
schema diff, and the Insight-side CI do not exist yet. The §2.4 async migration and §2.9 auth
enforcement remain deferred by decision. Per-section implementation status is stated where it
differs from this line; do not read the header as a blanket claim.
**Amendment log:** 2026-08-24 (M3) — P2 gains `effective_configuration`; §2.8 gains `ledger`;
§3.1 gains `configuration`. 2026-08-24 (doc repair, reviewed) — Status now states §4.3's
partial implementation rather than claiming it whole; §1 and §2.8 corrected to shipped values;
§2.6 records the deployment interaction; §3.1 places the ledger; §4.4 records which artifact is
authoritative for what; §5.6/§5.7 carry two existing rules the document never held. P2 and §2.7
are reconciled on a three-term key (review decision), and the in-Report reproducibility string
was corrected to match — moving `pipeline_version` from `77f014d78885` to `3665b88553ad` with no
change to any calculation, threshold, or numerical analytical output; the Report metadata
output itself changed. §1 states what a version change does and does not assert; §1.1 fixes the
scope of each identifier. §2.8 response freshness remains Open. 2026-08-28 (Q4) —
`ledger.durable` becomes an observed write-health signal instead of an environment-variable
mirror.
**Relationship to `WEBSITE_CONTRACT_W0.md`:** W0 remains the source of truth for the
**semantic analysis contract** (S1–S10 field mapping, outcome meaning, and frontend IA). The
Pydantic models and committed JSON Schema govern machine shape and nullability (§4.3–§4.4).
This document does **not** replace or restate W0. It governs only the
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
effective_configuration = g(snapshot_id, analysis_params, pipeline_version)
report                  = f(snapshot_id, analysis_params, pipeline_version)
```

Nothing outside those three terms may affect a single byte of `report`. Same snapshot, same
params, same version → byte-identical report, on any machine, at any wall-clock time. This is
the product's credibility claim (Delta is a relationship lie-detector), and it is what makes
`snapshot.hash` meaningful.

The **effective configuration is a published result, not a fourth input.** The algorithm may
branch on its own data, and `report.configuration` exists so a consumer can see which branch
ran (§3.1) — but every branch input must already be inside the snapshot or the explicit params,
which is what keeps `f` a three-term function. Any override a user can set is an analysis
param and belongs in the second term. If a value ever influences the outcome without being
derivable from those three, that is a violation of P2, not a reason to add a fourth term.

**P3 — `baseline_only` is a success.**
HTTP `200`, `outcome: "baseline_only"`. It is the product's signature state, not an error
and not "no data". No error code may ever be minted for it. (W0 §1.)

**P4 — Additive-only within v1.** See §4.

---

## 1. Version identifiers

| Identifier | Lives in | Changes when | Example |
|---|---|---|---|
| `api_version` | URL path + Run envelope | transport/resource shape changes | `v1` |
| `schema_version` | Report body | Report JSON schema changes | `delta.report.v1` **(frozen — do not rename)** |
| `pipeline_version` | Report body | the report-producing analysis **or adapter** implementation changes | `s10.sha256.3665b88553ad` |

`pipeline_version` is the field that explains "same data, different result". It is part of the
reproducibility triple (P2) and therefore belongs in the Report, alongside
`producer: "nestor-delta"`.

**What a version change does and does not assert.** It identifies *source-level provenance*:
the implementation that produced this Report is byte-identical to the implementation that
produced any other Report carrying the same value. It does **not** by itself imply that
numerical outputs changed. A corrected comment, a reworded metadata string, or a refactor that
leaves every number identical will all move it, and that is correct — the Report's content and
its stated semantics are part of what the field covers. Reading a moved version as "the maths
changed" is a misreading of the field, not a defect in it.

The converse also holds and matters more: two Reports sharing a value were produced by the same
implementation, which is the guarantee the field exists to give.

**`pipeline_version` is derived, never hand-written.** It is a SHA-256 over the contents of
`versioning.py`, `adapter.py`, and every module under `src/nestor_delta/`, rendered as
`s10.sha256.<first 12 hex>`. The example above is a real value, not a placeholder: an earlier
hand-authored example string from this document was copied into code as the live value and
stayed constant across a release that changed every report's numbers — the exact failure the
field exists to prevent. Any example shown here must be a value the code actually produced.

### 1.1 Scope of each identifier — do not widen `pipeline_version`

The API layer (`app.py`, `boundary.py`, `schema.py`, `errors.py`, `eurostat.py`) is deliberately
**outside** the hash, as is the web build. That is the correct boundary: folding routing, CORS,
ledger, or caching changes into `pipeline_version` would produce version movements unrelated to
the Report, which devalues the one field whose worth is that every movement means something
about the Report.

| Identity | Covers | Lives in |
|---|---|---|
| `pipeline_version` | Report computation and assembly | Report body |
| `api_version`, `schema_version` | compatibility boundaries | URL/Run envelope, Report body |
| `source_revision` | the commit a running process was built from | `capabilities` and `/health`; the web sidebar |

**A current `pipeline_version` proves only that the analysis and adapter build is current.** It
is not evidence that the API deployment or the web deployment is up to date; those are checked
with `source_revision`.

**`source_revision` is a source revision, not a deployment identity, and the distinction is
load-bearing.** It answers "which commit is this process running". It does **not** say when the
process was deployed, and two tiers reporting the same value were built from the same source
rather than deployed together — API and web are independent deployments and can drift apart
while agreeing here. A true deployment identity is not available: this project deploys by CLI
upload, so the platform exposes no commit or deployment variable of its own.

Resolution order is `RAILWAY_GIT_COMMIT_SHA` (platform, absent for CLI-upload deploys), then
`NESTOR_BUILD_SHA` (stamped per deploy by `scripts/deploy-railway.sh`), then a local
`git rev-parse`, then `"unknown"`. Platform first, so a stale hand-set variable can never
shadow an authoritative one. Candidates are accepted only as 7–40 hex characters after
stripping; blank and malformed values are skipped rather than passed through.

`NESTOR_BUILD_SHA` **must be written immediately before each deploy and never set by hand in a
dashboard.** A variable that survives the next deploy is a hardcoded version string — the exact
defect §1 records `pipeline_version` having had.

**`"unknown"` in a live deployment is a defect, not a benign default.** It means the process
cannot say what it is, and the field must not be read as "current".

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

**Deployment interaction.** The store is process-local, so any platform behaviour that ends
the process — a serverless sleep, a restart, a redeploy — empties it before `max_runs` is
reached. `max_runs: 100` is a ceiling, not a promise. Deployments that advertise retention
must keep the API process resident.

### 2.7 Idempotency

Because `snapshot_id` is content-addressed (§3.2), the reproducibility triple
`(snapshot_id, analysis_params, pipeline_version)` is a natural idempotency key. A repeat
submission of an identical triple **may** return the existing run instead of recomputing.
Optional in v1; the key must exist regardless.

The key is three-term because `effective_configuration` is derived from exactly these three
(P2) and so adds nothing to it. Adding a fourth term here would not make the key stricter — it
would only hide the fact that a configuration not derivable from the triple is a P2 violation.

### 2.8 `GET /api/v1/capabilities`

Unauthenticated and cheap. Minimum contents:

```jsonc
{
  "api_version": "v1",
  "report_schema_version": "delta.report.v1",
  "pipeline_version": "s10.sha256.3665b88553ad",
  "inputs": { "bundled_cases": ["..."], "csv_upload": true, "max_upload_bytes": 5242880 },
  "eurostat": {
    "enabled": true,
    "presets": [
      { "id": "es_industry_vs_construction_confidence",
        "label": "ES industry vs construction confidence",
        "dataset": "ei_bssi_m_r2" }
    ],
    "dataset_search": false
  },
  "execution": { "mode": "sync" },
  "run_retention": { "mode": "in_memory_process_lifetime", "max_runs": 100 },
  "ledger": {
    "enabled": true,
    "configured": true,
    "durable": true,
    "writable": true,
    "last_write_ok": true,
    "lines": 42,
    "path": "/data/relationship_ledger.jsonl",
    "write_probe_error": null,
    "observed_at": "2026-08-29T00:00:00Z"
  },
  "features": { "pdf_export": false, "report_persistence": false, "sharing": false }
}
```

Preset entries are three-part by contract: `id` is the stable identifier consumers key on,
`label` is display text that may change freely, and `dataset` is the machine-readable source
code. Never key on `label`.

This is how Insight learns which Eurostat presets exist without hardcoding them, and how it
learns the day `execution.mode` flips to `"async"`.

`ledger.configured` only reports deployment intent: whether
`NESTOR_RELATIONSHIP_LEDGER_PATH` points away from the default `/tmp` path. `ledger.writable`
is a cached same-directory write/read/cleanup observation, refreshed at most once per 60
seconds and updated immediately by a real append. `ledger.last_write_ok` is the most recent
real append outcome, or `null` before any selected relation has been written to the observed
path in this process. `ledger.lines` is counted once when a path is first observed and then
incremented by this single writer after successful appends; it is not a full-file scan on the
unauthenticated discovery path. `ledger.durable` is conservative: it is true only when a
non-default path is configured and the latest write observation passes. Ordinary `/health`
and `/api/v1/capabilities` requests inside the TTL read this bounded in-process observation
without touching disk; the first request after expiry performs only the constant-size probe,
not a full ledger scan while the prior line count is known. A new or newly recovered path is
counted once to initialize that observation. `ledger.observed_at` is the UTC time at which the
cached observation was last refreshed by a probe or real append; cache hits preserve it so
callers can see that the health value may be up to 60 seconds old. None of these fields prove cross-restart
persistence; deployments that claim a durable record must still mount persistent storage and
verify it outside the process.

Known limits: `ledger.lines` is a process-local incremental estimate. An external append,
truncate, or file replacement can make it drift until process restart or path recovery; this
does not change report content or ledger writes. A crash or forced kill can also leave a
same-directory `.probe-*` file. Such a file is not counted as ledger content, but may remain
until operational cleanup. Automatic cleanup is intentionally deferred because one process
cannot safely distinguish another live process's probe.

The API must remain at `--workers 1`. Each worker would otherwise own a different observation,
TTL, line estimate, and `last_write_ok`; `LEDGER_LOCK` is not cross-process, and concurrent
JSONL appends have no process-wide consistency guarantee. Keep one worker until both `RunStore`
and ledger observation/write coordination use shared, process-safe storage.

> **Diagnosed — deployment response freshness.** Capabilities and `/health` declare
> `Cache-Control: no-store`, but the historical defect was not an application cache. A controlled
> 2026-08-29 experiment proved that setting `NESTOR_BUILD_SHA` starts a redeploy of the prior
> uploaded source and that this redeploy can serve public traffic. Because the current deployment
> script sets the new revision before uploading the new source, prior code can temporarily report
> the new revision while returning its old capabilities shape. Cache-busting cannot prevent that.
> Diagnosis evidence is in `docs/evidence/Q3_VARIABLE_REDEPLOY_2026-08-29.md`. The deployment
> script is intentionally unchanged in this diagnostic round and must be repaired before the next
> production source deploy.

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
| `schema_version`, `producer`, `pipeline_version` | Report | part of the reproducibility tuple |
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

**The selected-relation ledger is a Run-boundary sidecar, not Report content.** It is an
append-only record of relations a completed run selected, written outside the Report body so
the Report stays a pure function. Its contents and durability rules live in
`WEBSITE_BACKEND_CONTRACT.md`; capabilities advertises it per §2.8.

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

**Status: partly implemented.** Live today: Pydantic models generate the committed JSON Schema,
and Delta-side tests validate responses against it, including the unknown-enum / extra-field
fixture. Not built: the versioned artifact shared by both repos, the build failure on a
non-additive schema diff, and the Insight-side CI. The bullets below are the target, not a
description of the current pipeline.

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

### 4.4 Which artifact is authoritative

When the project docs, the repository docs, the code, and a live deployment disagree, the
answer depends on *what kind of question* is being asked. There is no single winner.

| Question | Authority |
|---|---|
| What shape is this field, is it nullable, what type? | Pydantic models + the committed JSON Schema |
| Is this number correct — does the detector detect? | The frozen S7–S10 rules + the ground-truth fixtures |
| What does this field *mean*, and what may a surface do with it? | The accepted contracts and specs — `WEBSITE_CONTRACT_W0.md` first, then this document, then the visual spec |
| What is actually running right now? | The deployment itself: capabilities fetched with a cache-busting parameter, service logs, and inspection of real storage |

**"Code plus tests wins" is explicitly rejected as a general rule.** Code and its tests can
encode the same mistake together and stay green indefinitely. The worked example is in this
project's own history: `effect.score` was read from a 36-month rolling window while being
presented as the full-sample effect, overstating the product's headline number by 14% in the
over-claiming direction — and all 132 tests passed throughout. What caught it was a fixture
whose answer was known by construction, which is why algorithmic truth sits with ground truth
rather than with the test suite at large.

The practical rule that follows: a decision is not settled until the artifact named above for
its kind of question has been changed. Updating prose alone settles nothing; updating code
alone settles nothing a reader can discover.

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
flags come from `/api/v1/capabilities`. Key on preset `id`, never on `label` (§2.8).

**5.7 Never render `noise_floor` as a gate.** It is a diagnostic comparison scale and gates
nothing in v1 (W0 §3). A UI that shows it as a threshold, a floor beneath a score, or a
pass/fail badge is asserting a selection rule that does not exist.

---

## 6. Explicitly out of scope for this document

Deferred by decision, not by oversight:

- **Job queue / worker / async execution** — shape reserved (§2.4), implementation deferred
  until there is measured need.
- **Sub-resource endpoints** (`/runs/{id}/audit`, `/transforms`, `/evidence`) — the Report is
  the atomic unit; fetching parts separately risks serving pieces from different runs. If
  payload size becomes a real problem, add `GET /api/v1/reports/{id}?include=audit,transforms`
  rather than independent resources.
- **Durable persistence, accounts, tenancy enforcement, share links, PDF export** — no fields
  or endpoints are being designed for these beyond the reserved `requested_by` / `tenant_id`
  slots in the Run envelope and the auth stub in §2.9.
- **Generic Eurostat dataset search / indicator catalogue** — not implemented; capabilities
  reports `dataset_search: false`.
- Anything governed by `WEBSITE_CONTRACT_W0.md`.
