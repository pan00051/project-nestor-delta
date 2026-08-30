# Nestor Delta — Demo Milestones & Acceptance Boundaries (v1)

**Goal of this cycle:** a publicly reachable Delta that a potential customer or investor can
be shown — and can touch — without the author driving it.

**Two decisions this plan is built on:**

- **Streamlit is the shipping UI this cycle.** The HTML visual design is not built this cycle;
  it is reduced to a *specification* (M3) that survives into the next-phase real frontend.
- **The audience is external.** This makes evidence, not engineering, the critical path: a
  lie-detector that only ever says "no" is indistinguishable from a broken one.

**Document roles — these are upstream/downstream, not alternatives:**

| Document | Role |
|---|---|
| `WEBSITE_CONTRACT_W0.md` | Analysis contract — authoritative on schema and outcome semantics |
| `API_BOUNDARY_V1.md` | Insight⇄Delta integration contract — **the dependency contract of M1** |
| **this document** | **The execution plan for this cycle** — sequencing and acceptance only |

This document adds no schema and no API surface. Where it appears to define one, the other two
win. If only one document is used as the current working reference, it is this one; but M1 is
not implementable without `API_BOUNDARY_V1.md`.

**Amendment log**

- 2026-08-30 (verification-mechanism correction): M0 no longer claims an automated remote runner
  because this repository has no workflow configuration. The verification text now records
  the actual clean-venv install and full-pytest procedure. Historical counts, hashes, and
  acceptance conclusions are unchanged.

---

## 0. The one acceptance boundary that matters

Everything below is subordinate to this. If this passes, the cycle is done; if it fails, no
amount of green milestones compensates.

> **Demo DoD** — A person who has never seen Delta opens a public URL on their own device and,
> without the author touching anything, reaches all three of:
>
> 1. a case where Delta **selects** at least one relation and shows *why* it survived
>    (effect vs noise floor, stability, lifecycle, evidence gate);
> 2. a case where Delta **refuses** to conclude (`baseline_only`) and shows *why* it refused;
> 3. their **own CSV** uploaded, producing either a data-audit result or a human-readable
>    `422` telling them what to fix.
>
> The contrast between (1) and (2) is the pitch. (1) alone reads as a generic forecasting
> tool; (2) alone reads as a broken product.

**Explicitly outside this cycle's acceptance:** accounts, report persistence, share links,
PDF export, generic Eurostat dataset search, the real frontend, async job queue, custom domain.
`/api/v1/capabilities` must report each of these as `false` rather than hiding them.

---

## 1. Milestone map

| ID | Milestone | Gates | Parallel with | Size |
|---|---|---|---|---|
| **M0** | Evidence calibration | blocks M4, M5 | M1 | M (2–4 d) |
| **M1** | API boundary + Streamlit as API consumer | blocks M2, M4 | M0 | M (2–4 d) |
| **M2** | Thin-slice deployment (full stack, one case) | blocks M4 iteration, M5 | M3 | S–M (1–3 d) |
| **M3** | Visualization specification | blocks M4 | M2 | S–M (1–3 d) |
| **M4** | Charts in Streamlit + CSV human acceptance | blocks M5 | — | M–L (3–5 d) |
| **M5** | Rehearsal + freeze | — | — | S (1 d) |

Sizes assume one person working with AI assistance and are for *relative* sequencing, not
commitments. **M0 is the only milestone that cannot be compressed** — it can fail, and failure
changes the demo narrative. M3 and M4 are the compressible ones if a hard date appears.

**Start M0 and M1 on the same day.** M0 carries discovery risk and the longest lead time;
M1 is predictable engineering that does not depend on it.

---

## M0 — Evidence calibration

**Why first:** this is the only milestone that can fail for reasons no amount of work fixes,
and the entire demo narrative depends on the outcome. Discovering it late is the single
largest schedule risk in the cycle.

### Definition of done

1. **`S-GT-1` positive control** — a synthetic dataset with a deliberately injected lagged
   relationship (known lag *k*, known sign, known strength) runs through S1–S10 and produces
   `outcome: "ok"` with that relation `selected: true`, `reason_code: "selected"`, recovered
   lag == injected *k*, and correct sign. Committed as an automated test.
2. **`S-GT-2` negative control** — a synthetic pure-noise dataset produces
   `outcome: "baseline_only"`, `selected_count: 0`. Committed as an automated test.
   *A detector that selects nothing and a detector that selects everything are equally broken;
   both controls are required.*
3. **A positive demo case exists** — satisfied by *either* of two equally acceptable outcomes:
   **(a)** a real dataset producing ≥1 selected relation, snapshot frozen, hash recorded,
   Report JSON archived; **or** **(b)** `S-GT-1` explicitly promoted to the demo's
   positive-control case, with that decision and its rationale recorded.
   *Neither branch is a failure of M0.* (b) is a different demo narrative, not a worse one.
   What fails M0 is having no positive case at all — or manufacturing one by loosening
   thresholds.
4. **One real `baseline_only` case** — already satisfied by the `ei_bssi_m_r2` preset;
   re-run and archive its Report JSON as a demo fixture.

### How it is verified

Both controls are run manually from a clean virtual environment:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/pip install -e '.[dev]'
.venv/bin/python -m pytest -q
```

Both real cases are executed end to end (fetch → freeze → SHA-256 → audit → S1–S10) and their
Report JSONs are committed as demo fixtures, so the demo never depends on a live run.

### Scope guard — the important one

**Do not loosen evidence-gate thresholds to manufacture a positive case.** That converts the
product into the thing it exists to refute. Any threshold change must be justified by
`S-GT-1`/`S-GT-2` moving in the correct direction *together*, and must be recorded with its
before/after effect on both controls.

For the real `ok` case, favour series with a mechanically plausible lead-lag at monthly
frequency (new orders → industrial output, permits → construction output, registrations →
fuel consumption) over hunting through macro aggregates for a correlation.

### Failure branches

- **`S-GT-1` fails** → the gate is mis-calibrated for differenced monthly series. This is a
  bug, not a data problem, and it is a *valuable* find. Fix it before anything downstream;
  it would otherwise have been discovered during the demo.
- **Controls pass but no real dataset selects** → the demo narrative becomes
  "ground-truth validation proves the detector detects; on real data it declines to
  over-claim." This is still a coherent and defensible story. `S-GT-1` becomes a demo asset —
  a calibration certificate — not merely a test. **M0 therefore cannot hard-block the demo.**

---

## M1 — API boundary + Streamlit as API consumer

Implements `API_BOUNDARY_V1.md` §2 (resource shape), §3 (Report/Run split), §4 (schema as
executable artifact).

### Definition of done

1. `POST /api/v1/runs`, `GET /api/v1/runs/{run_id}`, `GET /api/v1/capabilities` live locally;
   `POST /analyze` retained as an alias.
2. Run/Report envelope per §2.2; run status enum per §2.3; HTTP mapping per §2.5
   (validation errors carry **no** `run_id`; crashed runs **do**).
3. Bounded in-process run store per §2.6, with `run_retention` truthfully advertised in
   `capabilities`.
4. JSON Schema generated from Pydantic and committed; contract tests include a fixture with an
   **unknown enum value and an unknown extra field** that the reader must tolerate (§4.2).
5. Streamlit obtains **all** data over HTTP. No direct pipeline import.
6. The existing 132 tests remain green, plus the new ones.

### How it is verified

The hard test for (5): **disable the direct-import path entirely and confirm Streamlit is still
fully functional.** Self-report does not count. This is what proves `/api/v1` is sufficient for
the next-phase frontend — the alternative is discovering the API is half-blind months later,
when fixing it costs several times more.

### Scope guard

No job queue, no sub-resource endpoints, no auth implementation (dependency stub only), no
persistence layer.

---

## M2 — Thin-slice deployment

**Thin in the feature dimension, complete in the stack dimension.** The slice is *one bundled
case* — no Eurostat, no CSV upload, no charts. But the stack deployed is the full shipping
topology: public Streamlit calling FastAPI over HTTP per M1. Deploying the backend alone would
leave the largest integration unknown untested, and the Demo DoD requires something an outsider
can **touch**, not an API they can curl.

### Definition of done

A public URL where Streamlit is reachable and completes one bundled case end to end, plus four
unknowns answered **in writing**:

1. **Egress** — can the host reach Eurostat? Record yes/no. If no, the pre-frozen snapshot path
   becomes mandatory rather than preferred.
2. **Filesystem durability** — restart the service and check whether frozen snapshots survive.
   On most PaaS they will not. **Expected mitigation: ship demo snapshots inside the image or
   repo as immutable static assets.** For a demo this is strictly better — the snapshot is
   immutable, its hash is reproducible, and nothing depends on runtime state.
3. **Cold start** — seconds from cold to first interactive screen, measured for both processes.
   Record the number.
4. **Topology** — one service or two? Same origin or cross origin? Record the choice and what
   it implies for CORS and for the `API_BOUNDARY_V1.md` §2.9 auth stub.

### Topology rule

Whatever is deployed now, **the API base URL must be configuration, never a hardcoded
localhost**, and CORS must be enabled and actually exercised even in a same-origin deployment.
The next-cycle real frontend will certainly live on a separate origin; paying that cost as a
config value now takes minutes, whereas discovering it as a code change later costs a redeploy
cycle in the middle of frontend work.

### How it is verified

Open the public URL from a device that has never logged in and complete one bundled case
**through the UI** — not via curl.

### Scope guard

No custom domain, no TLS yak-shaving, no CDN, no accounts — and no charts, CSV, or Eurostat in
this milestone. A platform-provided URL is sufficient for this cycle.

### Demo-safety rule

**The demo's main path must not depend on a live Eurostat fetch.** Waiting on a 228-month fetch
in front of an audience, while betting the upstream API is healthy that day, is an avoidable
risk. Live fetch stays available as a bonus ("we can also pull it live"); the scripted path uses
pre-frozen snapshots.

### Consequence for later milestones

Once M2 lands, **M4 iterates against the deployed instance, not localhost.** This is the
cheapest available insurance against "worked locally, broke in production at rehearsal" — a
failure mode that, with a scheduled external audience, surfaces exactly when it is least
fixable.

## M3 — Visualization specification

Specification, not skin. Deliverable is a mapping from Report JSON fields to visual encodings —
the part of the earlier "clean up the HTML" task that retains value once the real frontend is
built next cycle.

### Definition of done

A spec covering, at minimum: relation map (width = effect, opacity = confidence,
colour = lifecycle, dashed/grey = decaying/dead — **never red alarm**), relation detail
(trajectory, uncertainty band, noise-floor line, transform + lag), evidence table, and the
confidence-components panel — with a defined rendering for **all four states**:
`ok`, `baseline_only`, `422 validation_error`, and **any nullable field being null**.

### How it is verified

Walk every fixture in `mock_reports_v1.json` through the spec. Each must produce a defined
screen. Null must render as an explicit "insufficient evidence" treatment — never `0`, never
an empty gap.

### Where to spend the time

**The `baseline_only` screen deserves more design effort than the `ok` screen.** For this
audience it is the screen that decides whether viewers read "this product is disciplined" or
"this product returned nothing."

### Scope guard

No HTML polish, no design system build-out, no component library. Wireframe fidelity is enough.

---

## M4 — Charts in Streamlit + CSV human acceptance

### Definition of done

1. All four states from M3 render for real in Streamlit, driven by the M0 demo fixtures.
2. CSV upload passes **human** acceptance against a deliberately diverse file set — the gap
   named in the current status, which automated contract tests do not close.

### CSV acceptance checklist (each must yield a readable `422` or a correct audit — never a crash, never "no data")

- missing month(s) in the middle of the range
- duplicate month
- extra/unexpected columns
- non-UTF-8 encoding (GBK, UTF-8-BOM)
- date format variants (`2019-07`, `2019/07/01`, `Jul-2019`)
- fewer observations than the minimum
- a highly persistent signal declared `none` (must be rejected per W0 §5)
- an entirely wrong file (an image renamed `.csv`)

### How it is verified

Run each item by hand and record the actual on-screen message. The acceptance question is not
"did it error" but **"would a stranger know what to fix from this message?"**

### Scope guard

No real frontend, no upload size engineering beyond the advertised limit.

---

## M5 — Rehearsal and freeze

### Definition of done

1. The full demo script executed end to end **twice**, timed.
2. One adversarial rehearsal: kill network access to Eurostat mid-demo and confirm the scripted
   path still completes on frozen snapshots.
3. One cold-start rehearsal: first load after idle, timed — this is what the audience actually
   experiences.
4. Code frozen; only demo-blocking fixes after this point.

### How it is verified

A demo checklist, fully green, executed against the public URL rather than localhost.

---

## 2. Risk register and cut lines

| Risk | Trigger | Response |
|---|---|---|
| No real dataset selects a relation | M0 item 3 unmet | Fall back to the ground-truth narrative (M0 fallback). Do **not** loosen thresholds. |
| `S-GT-1` fails | M0 item 1 | Stop downstream work; treat as a calibration bug. Highest-value find in the cycle. |
| Host filesystem is ephemeral | M2 unknown 2 | Ship snapshots in the image. Expected, already mitigated. |
| Host cannot reach Eurostat | M2 unknown 1 | Frozen-snapshot path only; `capabilities` reports live fetch as unavailable. |
| Schedule compresses | a hard date appears | Cut M3 fidelity and the M4 checklist tail. Never cut M0 or M5. |
| Streamlit cannot express an encoding | M4 | Degrade the encoding, record it in the M3 spec as a next-cycle item; do not restart on a real frontend mid-cycle. |

**Standing rule:** if a milestone's scope grows, cut fidelity, not acceptance. The three items
in §0 are not negotiable; everything else is.

---

## Appendix A — M0 execution record (accepted)

**Verdict: M0 accepted.** The evidence gate selects when it should and refuses when it
should, the `baseline_only` state now carries its quantitative result, and the headline effect
number matches its contract definition. Two defects are carried forward as **M3 blockers**
(§A.4); neither blocks M1.

### A.1 What was validated

| Control | Result |
|---|---|
| S-GT-1 positive | `true_driver` selected; lag 2 ✓, sign −1 ✓, `reason_code: selected` |
| S-GT-1 decoys | all three rejected, `below_fdr_corrected_effect` |
| S-GT-2 negative | `baseline_only`, `selected_count 0`, all 4 candidates reported with reasons |
| S-GT-2b | **0/20** false positives across unscreened pure-noise seeds |
| S-GT-3 | byte-identical across runs — the reproducibility claim holds |
| S-GT-5 lifecycle | 8 passed; `regime_off` correctly `decaying` |
| Regression | 132 original tests still green |

Final S-GT-1: `score 0.5844`, `noise_floor 0.2065`, `eff/nf 2.830`, `stability 0.6512`,
`sample_support 0.9947`.

### A.2 The score bug — what ground truth was for

`effect.score` was being read from **the last 36-month S9 rolling window**
(`step=190, window_start=154, window_end=190`) rather than the full training window. On the
S-GT-1 fixture it reported **0.6730** where the contract definition (`|transformed r|`,
W0 §3) gives **0.5844** — a 14% overstatement of the product's headline number, in the
over-claiming direction.

Fixed at `adapter.py:746`; S9 rolling now supplies only `stability` / `uncertainty` /
`lifecycle`. The corrected value was verified independently against the fixture to sixteen
significant figures (0.5844220533473199 computed vs 0.5844220533473201 reported).

**No amount of real-data testing could have found this** — it requires data whose answer is
known by construction. This is the return on doing M0 before M1.

### A.3 Decisions recorded

- **Block 2 → option B.** `noise_floor` remains a diagnostic field and does **not** gate in
  v1; the formal selection logic is FDR + stability + uncertainty + sample support. The UI
  must therefore never render it as a pass/fail badge. Documented in the backend contract.
- **Block 3.** `baseline.mae` is now computed unconditionally (`adapter.py:814`);
  `baseline_only` reports carry `mae 0.7898` rather than `null`.
- **M0 branch (b).** No real `ok` case yet; S-GT-1 is promoted to the demo positive case,
  labelled as a synthetic ground-truth calibration control. Per §A.5 this is provisional —
  the search for a real case remains worthwhile.

### A.4 Carried forward — M3 blockers

**1. Lifecycle states are wrong on two of five drift profiles.**

| Profile | Ground truth (1st qtr → last qtr) | Reported | Correct |
|---|---|---|---|
| `constant` | 0.6309 → 0.6318, time-invariant | `strengthening` | `stable` |
| `linear_decay` | 0.5918 → 0.2767, monotonic decay | **`birth`** | `decaying` |
| `regime_off` | 0.6309 → 0.2125, stops at 70% | `decaying` ✓ | — |
| `regime_late` | 0.2294 → 0.6318, starts at 30% | `strengthening` ✓ | — |

`linear_decay → birth` is the serious one: W0 §7 colours the relationship map by lifecycle
state, so a fading relationship would render as a new one — a failure in the over-claiming
direction, which is the direction this product cannot afford. The S-GT-5 assertions did not
catch it because they only constrained `regime_off`, `regime_late` and `constant`; the
assertion set is under-specified and should be tightened when this is fixed.

Also noted: `regime_late` returns a `stability` identical to `constant` to sixteen digits,
which implies stability reflects only recent windows and cannot distinguish "always held"
from "only recently held". Defensible as a definition of current reliability — but it should
be a documented choice rather than an accident.

**2. `p_value: 0.0`** is underflow, not a p-value. Report a floor (`< 1e-12`) or log-space
value. Cosmetic, but a numerate viewer reads an exact zero as sloppiness.

### A.5 Correction to the Eurostat conclusion

The pre-fix analysis concluded `ei_bssi_m_r2` was "strong enough but unstable". **That
conclusion is stale — the score fix invalidated it and it was not re-derived.**

Corrected figures for `construction_confidence`, the best candidate: `lag` moved 3 → 2 (the
argmax was previously chosen on a 36-observation window), and `score` fell **0.499 → 0.2128**.

The detection floor at injected |r| = 0.30 corresponds to a training-window effect of
**0.3518**. Eurostat's best candidate reaches **0.2128 — 60% of that**, with `eff/nf` 1.188
against 1.703 at the floor point.

So the accurate statement is **weak *and* unstable**, not strong-but-unstable: the effect sits
below the strength at which the gate begins selecting at all, *and* stability is 0.047 against
a 0.45 gate. Anyone repeating the earlier framing to an audience is overstating the finding.

### A.6 Stability ceiling — reading (i) confirmed

S-GT-5 holds `beta_max` fixed and varies only the time profile:

| Profile | stability | selected |
|---|---|---|
| `constant` | 0.6512 | ✓ |
| `regime_late` | 0.6512 | ✓ |
| `intermittent` | 0.5401 | ✓ |
| `regime_off` | 0.3436 | ✗ |
| `linear_decay` | 0.3405 | ✗ |

`ceiling_excluding_constant = 0.6512 ≥ 0.45`. **Realistically drifting relationships can clear
the stability gate**, so the gate is not a ceiling disguised as discipline, and Eurostat's
0.047 is a property of that relationship rather than of real data in general.

Consequence for the plan: hunting for a real `ok` case is worth continued effort, and M0
branch (b) should be treated as the current fallback rather than the final answer.

---

## Appendix B — M1 execution record (accepted, with three M2 entry conditions)

**Verdict: M1 accepted.** The versioned resource shape is live, the Run/Report split holds, and
the M0 ground-truth suite reproduces identically through HTTP. Three defects (§B.3) must be
closed **before M2 deploys anything publicly**; none of them invalidate M1's work.

Repository consolidated first: M0 committed as `72e1082`, all work now in
`/Users/tianxu/Documents/Nestor Delta`. The stale `~/nestor-delta` skeleton is retired.

### B.1 The decisive check

`NESTOR_API_BASE=http://localhost:8000 pytest tests/ground_truth -v` → **21 passed**, identical
to in-process. That single line establishes what M1 existed to establish:

- `effect.score` still `0.5844220533473201` — the API layer did not perturb analysis semantics
- `baseline_only` arrives as **200**, not an error
- S-GT-3 still byte-identical through the HTTP path
- `report_body()` reports no Run-envelope leak, which makes API_BOUNDARY §3.1 field placement
  an executable check rather than a documented intention

Other results: 140 unittest (was 132), 21 ground-truth in-process, schema parity test, GET/POST
report equality, eviction → 404, 422 creates no run, 500 creates a `failed` run, unknown-enum
and extra-field fixture tolerated.

### B.2 Verified independently, not from the report

The M1 acceptance criterion for Streamlit was a kill test: disable the direct-import path and
confirm the app still works. The report offered `AppTest exception_count=0` and an HTTP 200 on
port 8501, **neither of which proves the absence of a direct-import fallback** — an AppTest run
can pass *because* of one.

Direct inspection settled it, and the result is better than the test asked for:
`src/nestor_delta_web/` imports only `streamlit`, `requests`, and its own modules — zero
references to `nestor_delta_service`, `analyze_payload`, or `nestor_delta.*`. There is no
direct-import path to disable because the web layer no longer has one. `api_client.analyze()`
posts to `/api/v1/runs` and unwraps `report`; the base URL is `DELTA_API_BASE_URL` with a
localhost default, i.e. configuration rather than a hardcoded host, as required.

The engineering is right; the evidence offered for it was not. Report the check that was asked
for, not a check that correlates with it.

### B.3 M2 entry conditions

**1. `PIPELINE_VERSION` is a hardcoded literal, and it is currently false.**

`boundary.py:17` sets `PIPELINE_VERSION = "s10.2026.08.1"` — the placeholder string invented as
an *example* in API_BOUNDARY_V1.md §1. During M0, `adapter.py:746` changed `effect.score` in
every report (0.6730 → 0.5844 on the control fixture). Diff a pre-M0 report against a post-M0
one and `pipeline_version` is identical while the numbers differ — exactly the failure the
field exists to prevent ("the field that explains *same data, different result*").

Derive it from the analysis and adapter modules (git describe, or a hash of their contents) and
ensure the M0 fix is reflected. A version string that does not move when behaviour moves is
worse than no version string: consumers trust it.

**2. Eurostat preset keys are display labels, not identifiers.**

`capabilities.eurostat.presets` publishes
`["ES industry vs construction confidence (ei_bssi_m_r2)"]`, because the label is the dict key
in `presets.EUROSTAT_PRESETS`. Capabilities is the discovery surface consumers are told to read
instead of hardcoding (API_BOUNDARY §5.6), so this makes a human-readable sentence into a
load-bearing identifier: renaming it breaks every consumer, it is awkward as a request
parameter, and the machine-readable dataset code is buried inside prose.

Split it: `{"id": "...", "label": "...", "dataset": "ei_bssi_m_r2"}`. Cheap now; breaking once
the surface is public.

**3. `/audit` and `/snapshot` were never versioned.**

`app.py` exposes `/api/v1/runs`, `/api/v1/runs/{id}`, `/api/v1/capabilities` — but `/audit` and
`/snapshot` remain unversioned, and `api_client` calls both. The Streamlit app therefore speaks
to a mixture of versioned and unversioned endpoints, which partially defeats the point of the
version prefix: two of the three things the frontend calls are not on the stable surface.

(`/analyze` is exempt — it is the declared legacy alias.) This was an omission in the M1
instruction, not a deviation from it: the two endpoints were not known when the task was
written. Add `/api/v1/audit` and `/api/v1/snapshot`, keep the bare paths as aliases.

Also outstanding, folded into M2 where it becomes real: CORS was added but never exercised.

### B.4 A pattern worth naming

Three findings across M0 and M1 share one shape — a field that looks authoritative but is not
wired to anything:

- `effect.score` read from a 36-month window while presented as the full-sample effect
- `noise_floor` rendered as a threshold while gating nothing
- `pipeline_version` published as provenance while hardcoded

For a product whose entire proposition is refusing to over-claim, decorative rigor is the most
expensive defect class available. Worth an explicit review pass before M3 binds any of these
fields to a visual encoding: **for every field the UI will render, name what would have to
change for that field to change.** If nothing would, it is decoration.

### B.5 Still carried from M0 (M3 blockers)

- Lifecycle mis-states: `linear_decay` → `birth` (should be `decaying`), `constant` →
  `strengthening` (should be `stable`). Tighten the S-GT-5 assertions when fixing.
- `p_value: 0.0` is underflow; report `< 1e-12` or log-space.

---

## Appendix C — M2 preflight (repository facts that amend the original M2 plan)

Established by direct inspection before writing the M2 instruction, so the instruction does not
repeat M1's omission of endpoints nobody had enumerated.

### C.1 The filesystem-durability unknown is not what M2 assumed

M2 §"unknown 2" anticipated frozen snapshots being lost on restart. Inspection shows **nothing
is written to disk at all**: `eurostat.build_eurostat_snapshot()` assembles CSV text in memory,
takes its SHA-256, and returns a dataclass. Bundled cases are already committed to git (14 files
under `cases/`). So ephemeral storage is a non-issue.

The real gap is the opposite one: **there is no frozen Eurostat snapshot artifact anywhere**, so
the demo-safety rule ("the main path must not depend on a live fetch") currently has nothing to
fall back on. `build_eurostat_snapshot` already accepts pre-supplied `snapshots` in the payload,
so closing this needs a committed fixture, not new code.

### C.2 Two deployment hazards that only appear in production

**Multiple workers break the run store.** `boundary.py:43` holds `RUN_STORE = RunStore()` as a
module-level singleton — process-local by construction. Under more than one uvicorn worker a
`POST` lands on worker A while the follow-up `GET /api/v1/runs/{id}` hits worker B and returns
404 non-deterministically. Deploy with exactly one worker, state it in the deploy config, and
treat multi-worker as blocked until a shared store exists. The store also has no lock; the
`while len(...) > max_runs: popitem()` eviction is not atomic under FastAPI's threadpool.

**`REPO_ROOT` assumes a source checkout.** `adapter.py:40` computes
`REPO_ROOT = Path(__file__).resolve().parents[2]` and resolves every bundled case beneath it.
That holds when running from the repository, and breaks the moment the package is pip-installed
into `site-packages` — where `parents[2]` is not the repo. Either guarantee checkout-style
execution or ship `cases/` as package data.

### C.3 Deployment surface

- **No deployment config exists** — no Dockerfile, Procfile, railway.json, fly.toml, or runtime pin.
- **One environment variable**: `DELTA_API_BASE_URL` (default `http://localhost:8000`). No secrets.
- **Endpoints**: `/api/v1/runs`, `/api/v1/runs/{id}`, `/api/v1/capabilities`, `/analyze`,
  `/audit`, `/snapshot`, `/health`, `/schema/report`. The last four are unversioned; `/audit` and
  `/snapshot` are live frontend dependencies (see Appendix B.3 item 3).
- **Python**: `requires-python = ">=3.9"`, but the working environment is 3.10. Pin explicitly
  for deployment rather than letting the platform choose.
- `private/` is empty and untracked; exclude it from any deploy artifact regardless.

### C.4 M1 is uncommitted

`git log` ends at `72e1082` (M0). M1's work — `boundary.py`, `schema.py`, `test_api_boundary.py`,
the committed schema, the API changes — is entirely in the working tree. Commit before M2 starts,
so a deployment problem can be bisected against a known-good tree.

---

## Appendix D — Railway serverless: resolved as a configuration decision, not a defect

**Observation.** On Railway, `api` (FastAPI) sleeps correctly — `Stopping Container` observed,
first request after sleep returns in 2.378 s TTFB. `web` (Streamlit) does not sleep, with no
`Stopping Container` after 20+ minutes of no new egress.

**Diagnosis.** The recurring flow from the web container targets `100.64.0.4`, which sits in
RFC 6598 CGNAT space (100.64.0.0/10) — Railway's internal edge network, not the public
internet, despite the `peerKind=internet` label. The byte counts (66 / 138 / 204 / 268) are
cumulative per-flow (+72, +66, +64), i.e. **one long-lived connection**, not repeated events:
the signature of a Tornado WebSocket ping/pong. Inspection confirms the application is not the
source — `railway.json` sets no `healthcheckPath`, and the Streamlit app has no autorefresh or
polling loop. The likely mechanism is that Railway's inactivity detection keys on a
proxy-observed connection rather than on byte flow, so a lingering upstream WebSocket prevents
the timer from starting. FastAPI, being stateless HTTP that closes each connection, sleeps
normally.

**Decision: do not fix it.** For a demo with a scheduled audience, a web service that refuses
to sleep is the desired behaviour — a cold start in front of viewers is far more costly than
the hosting fee. Serverless is therefore **disabled deliberately on both services** for the
demo period, recorded in the deployment doc with its cost trade-off. Root-cause investigation
(a minimal Streamlit control on the same platform) is optional and sits off the critical path.

**Cold-start figures corrected.** The 69.902 s measurement is void: no `Starting Container`
accompanied it and it includes browser-control latency. The valid figures are API 2.378 s TTFB
(corroborated by a logged `Stopping Container`), and for web, time from `Starting Container` to
first interactive page after a deploy or restart. Browser-automation timeouts are a
test-harness problem and are excluded from M2 acceptance — they measure Chrome's control
interface, not the product.

### D.1 The consequential finding: sleep destroys run storage

`RunStore` is process-local, and serverless sleep destroys the process. With serverless enabled
on `api`, `run_retention` really means "until the next 10 idle minutes", not the `max_runs: 100`
that `capabilities` implies to a consumer. A run submitted before a sleep returns 404 after
wake — which would bite precisely when someone wants to revisit an earlier report mid-demo.

This is a problem that appears when sleep works, not when it fails. Two actions: state the
relationship in `capabilities.run_retention` or the deployment doc, and keep serverless off on
`api` during the demo.

---

## Appendix E — M2 accepted; M3 preflight

**M2 accepted** at `24e841c`. Live endpoints verified independently by fetching
`https://api-production-9849.up.railway.app/api/v1/capabilities` — `pipeline_version`
(`s10.sha256.7763cf123030`), `run_retention`, and the three-part preset structure all match the
reported values.

| Unknown | Answer |
|---|---|
| Eurostat egress | Yes — live cloud fetch returned 228 rows hashing to the frozen fixture's `7f165372…a3664ca`. Demo still runs on the frozen snapshot. |
| Bundled case reachability | Yes — `spain_retail_eurostat_2008_2025` runs in the container, 216 observations, `REPO_ROOT=/app` resolves `cases/`. |
| Cold start | API wake 2.378 s TTFB; web restart-to-interactive < 2 s. The 69.902 s figure is void. |
| Topology | Two services, cross-origin. No real CORS consumer this cycle (Streamlit calls the API server-side); synthetic preflight verified for the next-cycle frontend. |

Online M0 suite: **21 passed**, `effect.score = 0.5844220533473201`, negative control HTTP 200.
Public URLs: api `api-production-9849.up.railway.app`, web `web-production-31a89.up.railway.app`.

### E.1 M3 is not greenfield — and two live defects say so

The Streamlit app already renders lifecycle badges, score, noise floor, stability, uncertainty,
confidence, a trajectory chart, and an evidence table (`render_logic.py` exposes ~25 view
helpers). M3 is therefore an **audit-and-correct** exercise before it is a specification
exercise. Two contradictions are already on screen:

**The landing copy contradicts the contract.** `streamlit_app.py:407` reads "…which directed
relationships survive the **noise floor**, lifecycle, and evidence gate." Block 2 was decided as
option B: `noise_floor` is diagnostic and gates nothing. The first sentence a visitor reads
claims a gate that does not exist.

**The score tile presents the noise floor as a threshold.** `streamlit_app.py:294` renders
`Score 0.5844` with `floor 0.2065` directly beneath it. Whatever the intent, a value shown under
its "floor" reads as pass/fail — which is precisely what decision B prohibited.

Both are the decorative-rigor pattern again (Appendix B.4), and both are visible to the demo
audience today.

### E.2 Facts M3 should not have to rediscover

- `trajectory` **is** populated (`adapter.py:747` via `target_source_trajectory`), so the detail
  timeline has real data; the null path is already handled honestly at `streamlit_app.py:302-306`.
- But `st.line_chart({"score": [...]})` discards each point's `date`, so the x-axis is an index,
  not time — weak for a product about temporal relationships.
- `docs/mock_reports_v1.json` is in the repo and is the four-state walkthrough fixture.
- `lifecycle_badge` / `lifecycle_steps` already drive visual state, which means the M0 lifecycle
  defect (`linear_decay → birth`) is **rendering incorrectly right now**. It must be fixed before
  any further encoding is specified on top of it.

### E.3 An open design question for M3

W0 §7 specifies a relationship map. With one target and four candidate signals, that map is a
star with four edges — at demo scale it may read as a toy rather than as evidence. Recommended
compromise: make the **ranked evidence table** the hero of the report screen, and keep the map
as a secondary view that earns its place once candidate counts grow. This honours W0 without
putting a four-edge diagram at the centre of an investor demo.

---

## Appendix F — M3 review: work sound, not yet shippable

The M3 changes are good; the milestone is not acceptable yet, for two reasons that are not
quality problems.

**Uncommitted.** `git log` ends at `24e841c` (M2). Seven modified files plus
`docs/M3_VISUAL_AUDIT_SPEC.md` sit in the working tree.

**Undeployed — and `pipeline_version` is what revealed it.** A cache-busted fetch of the live
`/api/v1/capabilities` still returns `s10.sha256.7763cf123030`, unchanged from before M3.
`classify_relation_lifecycle` lives in `src/nestor_delta/temporal_stability.py`, and that file
plus `adapter.py` are both inside the hash and both modified — so the hash must move once
deployed. It has not. The public demo is therefore still serving the pre-M3 build: the old
landing copy ("survive the noise floor…"), the score tile with `floor` beneath it, and the
incorrect lifecycle states — precisely the audience-visible contradictions M3 set out to fix.

This is the first time `pipeline_version` has done the job it was rebuilt for in M2. The field
we converted from a hardcoded placeholder into a content-derived hash has now caught a stale
deployment on its own. It has stopped being decoration.

**Tightened after the M3 documentation review.** State this claim narrowly. The hash covers
`versioning.py`, `adapter.py`, and `src/nestor_delta/` — so what it detected was a stale
**analysis-and-adapter build**. The API layer (`app.py`, `boundary.py`, `schema.py`,
`errors.py`, `eurostat.py`) and the entire web build sit outside the hash, and a current
`pipeline_version` is therefore no evidence that the API deployment or the web deployment is up
to date. Widening the hash to cover them would be the wrong repair: it would produce version
movements unrelated to the Report and devalue the one field whose worth is that every movement
means something about the Report. The separate identifier for that question is
`source_revision`, reported by both tiers (`API_BOUNDARY_V1.md` §1.1) — and it is a *source
revision*, not a deployment identity: equal values mean the same commit, not the same
deployment.

**The online M0 run proves nothing this round.** Only `test_ground_truth.py` was run online
(13 passed) rather than the whole directory as in M2 (21, now 26). The lifecycle fix is
verifiable only by the drift suite, which was not run against the deployment.

### F.1 Verified good

Test arithmetic is self-consistent: unittest 144 + ground-truth 26 = pytest 170; the drift suite
grew 8 → 13 with the tightened per-profile assertions.

The `evidence_gate.py` change — unmentioned in the report — was inspected and is a better fix
than was asked for. The old `2.0 * (1.0 - cdf(|z|))` catastrophically cancels at large |z| (cdf
rounds to 1.0, so the expression yields exactly 0.0); the replacement `2.0 * cdf(-|z|)` with a
`1e-300` floor takes the lower tail directly and is numerically stable. It repairs the **value**
rather than only its display. No threshold was touched.

That said, `evidence_gate.py` is the one file under an explicit prohibition ("do not loosen
evidence-gate thresholds"). Any change to it must be reported proactively, however benign —
otherwise a reviewer only finds it by reading diffs unprompted. This time the surprise was
favourable; that cannot be relied on.

### F.2 `intermittent → stable` needs a presentation rule

Ground truth for `intermittent` alternates on and off every 24 months (first quarter 0.4864,
last quarter 0.4181). The lifecycle enum has no vocabulary for "alive but discontinuous", so
`stable` is defensible among the five available labels — but it is the most over-claiming of
them.

The numeric layer does capture it: `intermittent` scores stability 0.5401 against `constant`'s
0.6512. The spec should therefore fix a rule: **a lifecycle label must never appear alone; it is
always presented together with its stability value.** Otherwise a viewer reads "stable" as "this
relationship has always held".

---

## Appendix G — Architectural principles agreed after M3 (not yet implemented)

Design decisions from the post-M3 discussion. None are built yet; they constrain how later work
may be built.

**G.1 Dependency direction between rigorous and approximate computation.**
An approximation may consume a rigorous result; a rigorous step may never consume an
approximation. The constraint is on dependency direction, not execution order. The M0
`effect.score` bug was a violation of exactly this — a 36-month rolling estimate standing in for
a full-window quantity — and its fix was this rule applied once. A second benefit of the
ordering: computing the exact value first gives a yardstick against which the approximation's
error can be measured at all.

What counts as an "approximation" needs care, or the rule becomes either vacuous or paralysing.
The test: **is this quantity a stand-in for something we could measure properly?** If yes, it
must not decide. If it is a genuinely different quantity the decision legitimately needs — as
`stability` is, measuring temporal consistency rather than strength — it is a measurement, not
an approximation, and it needs its own validation (which S-GT-5 provided).

This rule does **not** cover the choice of what to test in the first place; candidate selection
sits upstream of everything and is governed by pre-registration and attempt-counting instead.

**G.2 Principled vs learned adaptation.**
Test: can you write down *why* a parameter should change before seeing any data? If yes it is
principled adaptation — unimplemented mathematics, safe to build. If the answer is only "this
scores better empirically", it is learned adaptation and needs held-out generators, hard
constraints, and versioning. The noise floor and FDR threshold already adapt principledly.
Two gaps: the 36-month rolling window should scale with n rather than stay fixed, and
`lag_window` needs a principled *upper bound* (relative to sample size) rather than an
auto-chosen value — true lag is domain knowledge, not derivable from the data.

**G.3 Data-dependent branching is compliant with the reproducibility claim.**
`report = f(snapshot, params, pipeline_version)` still holds when the algorithm branches on its
own input — a function that branches on its argument is still a function. The adaptation must
depend *only* on what is inside the snapshot: never wall clock, caller identity, other users'
data, machine state, remote config, or **execution history** (the accidental one — careless
caching makes run N depend on run N−1).

Two obligations follow:

- **Publish the effective configuration.** Under branching, two reports sharing a
  `pipeline_version` may have been produced by materially different procedures, and a consumer
  would reasonably assume comparability. The report needs a `configuration` block carrying the
  effective parameter values and the rule that selected them. Same lesson as `noise_floor`:
  anything that influences the outcome must be visible in the report.
- **A ground-truth fixture per branch, including boundaries.** Existing fixtures are all
  n=216, so a small-n branch would never be exercised while real users hit it. Off-by-one at a
  branch threshold silently changes results for every dataset near it.

Design preference: **continuous adaptation over discrete branching.** "I added one data point
and it changed its mind" is more damaging to a product selling trustworthiness than any
parameter choice. Where discrete branching is unavoidable, show the rule to the user.

The claim therefore becomes: same data, same **effective configuration**, same version → same
result — with the effective configuration stated by the report itself.

**G.4 Cross-user threshold learning: rejected.**
Learning thresholds from a pool of user datasets would make a result depend on other people's
data. Reproducibility dies, the audit trail breaks ("rejected because of a threshold learned
from 4000 datasets you cannot see"), and consent obligations attach. If ever built, it must be
an explicitly opt-in labelled mode, never the default, never mixed into the default report.

**G.5 Outcome ledger — the only item with a time cost.**
Recording which selected relations actually held up out-of-sample builds a track record that
cannot be created retroactively, so it must start early. It is measurement, not optimisation,
so it is immune to the Goodhart problem, and it leaves reports pure — the ledger is a separate
append-only record (`run_id`, `snapshot_hash`, target, selected relations with lag/sign/score/
stability, `generated_as_of`, `pipeline_version`). A jsonl file suffices at demo scale.

A backtested version is available immediately: set `generated_as_of` to a past date, run, and
check the selected relations against subsequent actuals. It must be labelled backtest rather
than live record.

**G.6 Calibration vs fishing.**
The distinction is not how many runs but what serves as the criterion. Calibration judges
operating characteristics — sensitivity, false-positive rate, lag recovery — against
independently known answers, and any number of runs is legitimate. Fishing judges whether a
particular real case passed, and one run already contaminates it. Three rules: tune only on
ground truth; designate burnable calibration series separately from held-out demo series
in advance; log every run against real data.

---

## Appendix H — Lag-window sweep, profile shape, and an over-differencing finding

Attempt-log entry 1, plus three findings from it. All runs used the frozen `ei_bssi_m_r2`
snapshot, train window 2005-01..2019-12 (n=179 after differencing), everything except the swept
parameter held fixed.

### H.1 The lag-window hypothesis is refuted

Pre-registered criterion: if `lag_window=3` was truncating a longer-lead relationship, `stability`
would rise out of the 0.05 range. It did not.

| lag_window | argmax lag | score | noise floor | eff/nf | **stability** | reason |
|---|---|---|---|---|---|---|
| 3 | 2 | 0.2128 | 0.1791 | 1.188 | 0.0466 | insufficient_stability |
| 6 | 2 | 0.2128 | 0.1969 | 1.081 | 0.1229 | insufficient_stability |
| 9 | 2 | 0.2128 | 0.2066 | 1.030 | 0.0944 | insufficient_stability |
| 12 | 2 | 0.2128 | 0.2133 | 0.997 | 0.0753 | insufficient_stability |

The argmax stays at lag 2 in every window — widening the search finds nothing better, so the true
lag is not beyond 3. Widening actively **hurts**: the comparison count rises, the corrected noise
floor rises with it, and `eff/nf` falls monotonically until at `lag_window=12` the relation sits
below its own noise floor. `lag_window=3` is the most favourable setting for this case.

No parameter was changed as a result, so this case is not contaminated by parameter selection.
(It is contaminated for a different reason — see H.4.)

### H.2 Lag-profile shape is a third evidence axis

Correlation by lag, differenced, training window:

```
lag    0      1      2      3      4      5      6      7      8      9     10     11     12
r   +.056  -.116  +.213  -.094  -.047  +.124  -.008  +.069  -.025  +.114  -.053  +.075  -.042
```

**Eleven sign flips out of twelve transitions.** A real transmission mechanism spreads its effect
over adjacent months and so produces a smooth, single-signed hump; the peak at lag 2 here is an
isolated spike flanked by opposite-signed values. Under pure noise roughly six flips would be
expected, so eleven is *more* alternating than chance — a separate signal in its own right (H.3).

This gives a third axis, independent of the two in use: `score` measures strength, `stability`
measures consistency **over time**, profile shape measures consistency **over lag**. It is nearly
free — the pipeline already computes every lag to take the argmax and discards the rest.

### H.3 The transform guard is one-sided, and it forces over-differencing here

| series | level lag-1 ACF | differenced lag-1 ACF | range |
|---|---|---|---|
| `industry_confidence` | +0.966 | −0.147 | [−38.3, 5.6] |
| `construction_confidence` | +0.920 | **−0.437** | [−69.9, 35.5] |

A differenced lag-1 ACF near −0.5 is the textbook signature of **over-differencing**: differencing
an already-stationary series induces exactly this. And these are survey balances — bounded in
[−100, 100] and mean-reverting by construction, so a unit root is not physically available to them.

Declaring `none` is refused: `high_persistence_requires_transform`, "Signal
'industry_confidence' has lag-1 ACF 0.968 but was declared 'none'." So the only admissible
transform is the one that over-differences.

The guard is asymmetric. W0 §5 catches "you should have differenced" and nothing catches "you
should not have". Underneath sits a deeper limit: **a lag-1 ACF cannot distinguish a stationary
AR(1) with φ≈0.95 from a random walk** — that is what unit-root tests (ADF / KPSS) exist for — yet
an irreversible transform decision is made on that statistic alone.

Consequences: over-differencing removes the low-frequency component where an economic relationship
would live, amplifies high-frequency noise, and mechanically induces the alternating
cross-correlation profile seen in H.2.

**Therefore the `baseline_only` verdict on this pair is not clean evidence that the pair is
unrelated.** The honest statement is narrower: *the pair has not yet been fairly tested.*

### H.4 Bookkeeping

The lag profile in H.2 was computed on the real case before being validated on ground truth.
`ei_bssi_m_r2` is therefore now a **calibration case** for the profile metric and cannot serve as
independent evidence of that metric's discriminating power.

Also carried forward: all four runs report `lifecycle: birth` for a relation with stability 0.047.
"Birth" reads as *emerging, promising, just early* when nothing is there — an over-claiming
default. Proposed rule: a relation whose stability is below the gate may not be labelled `birth`;
it needs an explicit insufficient-evidence state.

And `uncertainty` swung 0.381 → 0.335 → 0.034 → 0.462 across a parameter that changed neither the
reported lag nor the score. A tenfold excursion in a diagnostic under those conditions suggests
estimation instability worth a look.

---

## Appendix I — Plan: profile axis and transform diagnostics

Ordered by return, with fallbacks, acceptance criteria, and the bias boundaries that govern all
of it. Nothing here is built.

### I.1 P0a — over-differencing diagnostic (first; it is a correctness gap, not a feature)

After the declared transform is applied, measure the transformed series' lag-1 ACF and flag values
below −0.3 in `data_audit` as a probable over-differencing warning.

**Strictly additive: 参考级 only.** It changes no threshold, no selection, no outcome. The point is
to make an existing silent bias visible, not to act on it yet.

*Acceptance* — flags `construction_confidence` (−0.437); does **not** flag the synthetic fixtures,
whose differenced innovations are white by construction; every existing test still passes with
identical values, including `effect.score = 0.5844220533473201`.

### I.2 P0b — replace the ACF heuristic with a real stationarity test (later, gated)

A lag-1 ACF cannot separate a near-unit-root stationary process from a random walk. An ADF/KPSS
pair can. This changes which transforms are admissible, so it is a **gate change** and falls under
the M0 rule: it may only be adopted if S-GT-1 and S-GT-2 move in the same direction, with
before/after recorded for both.

Not before the demo. It is a statistical commitment, not a patch.

### I.3 P1 — lag profile as a third axis (parallel with P0a)

1. Expose the full lag profile in `RelationView` — the values already exist and are discarded.
2. Derive shape metrics: sign-flip count, peak-to-neighbour ratio, a smoothness measure.
3. **Validate on ground truth before it informs anything about real data.** Expect a smooth
   single-signed hump on S-GT-1 and chance-level alternation on S-GT-2.
4. Report the metric's distribution across N seeds for positive vs negative fixtures, and state the
   separation achieved.
5. **Independence check**: correlate the shape metric with `stability` across all fixtures. High
   correlation means it is a proxy for an axis already measured properly — in which case, by the
   G.1 rule, it must never decide.

*Acceptance* — 参考级 on delivery. Promotion to 判定级 requires a stated separation threshold agreed
**before** the measurement, plus passing the independence check. If either fails, it stays
参考级 permanently.

Worth building even if it never gates: a smooth hump beside a jagged comb is a picture an audience
reads in two seconds, and it shows the product's thesis rather than asserting it. That also
addresses the "charts are scattered and unintuitive" complaint with a single figure.

### I.4 Fallback ladder

| If | Then |
|---|---|
| P1's metric does not separate, or is a stability proxy | Keep it display-only; it is still the best demo figure available. Move to data replacement. |
| P0a confirms over-differencing but P0b's proper test still forces `diff` | The pair has then been fairly tested and `baseline_only` stands as a real verdict. Move to data replacement. |
| Data replacement (the five mechanism-chosen candidates) yields no `ok` | M0 branch (b): synthetic positive case, ground-truth demo narrative. Already established as legitimate. |
| Everything fails | The demo is the ground-truth narrative plus a real refusal. That was always a defensible story; it is the floor, not a cliff. |

Candidate selection, if it comes to that, is governed by one lesson from H.1: **`stability` is the
binding constraint, not `score`.** Choose for mechanically enforced persistence — supply chains,
cost pass-through, physical process delays — not for historical correlation.

### I.5 Bias boundaries (governing all of the above)

1. **Ground truth precedes real data.** Every new metric is validated on synthetic fixtures with
   known answers before it informs any judgement about a real case.
2. **Pre-register.** Expected values are written down before the run. H.1 is the worked example: a
   criterion was fixed in advance, the result contradicted it, and the hypothesis was dropped
   rather than reinterpreted.
3. **No metric may be introduced because it rescues a specific real case.** The decision to build
   must precede seeing its effect on real data. Where that ordering was already broken — the
   profile metric, see H.4 — the case is logged as calibration and cannot double as independent
   evidence.
4. **Independence required.** A new axis that correlates strongly with an existing one is a proxy,
   not an axis, and may not decide.
5. **判定级 / 参考级 declared in advance**, never retrofitted after seeing which is convenient.
6. **Every real-data run is logged** — parameters, outcome, date — including the unflattering ones.
7. **Calibration set and demo set are separated in advance.** `ei_bssi_m_r2` is now firmly
   calibration (H.1, H.4) and may not be presented as independent evidence.

---

## Appendix J — M3 accepted; four M3.5 entry conditions

**Verdict: M3 accepted** at `ad77fd3`, working tree clean. All three Appendix F blockers are
closed, and closed with the right kind of evidence. Four defects (§J.3) are carried into M3.5;
none of them invalidate M3's work.

Commits in this milestone: `5a268ce` (visual audit fixes), `facb43d` (p-value display),
`71169b2` (baseline screenshot), `78e2c2f` (configuration + ledger safeguards), `ad77fd3`
(ledger path logging).

### J.1 Appendix F's blockers — verified independently

| F blocker | Status | Evidence |
|---|---|---|
| Uncommitted | Closed | Five commits above; `git status` clean |
| Undeployed | Closed | Live `/api/v1/capabilities` returns `s10.sha256.77f014d78885`, moved from the pre-M3 `s10.sha256.7763cf123030` |
| Online M0 run incomplete (13 of 26) | Closed | 26 passed online; `effect.score` still `0.5844220533473201` |

`pipeline_version` has now completed its loop across two consecutive milestones: in F it caught a
stale analysis-and-adapter build, here it proves a live one. That is the return on the M2 decision
to make it content-derived rather than a literal — within its scope, which is the Report-producing
implementation only. It says nothing about whether the API or web deployment is current (see the
tightening note in Appendix F and `API_BOUNDARY_V1.md` §1.1).

The report also disclosed the `evidence_gate.py` situation proactively, which is the F.1 process
lesson landing. Verified: `git diff 71169b2..HEAD -- src/nestor_delta/evidence_gate.py` is empty,
so the report's account of this round is accurate.

### J.2 Verified better than reported

- **The ledger schema is complete against G.5**, not merely present. `boundary.py:156` writes
  `mode` / `run_id` / `snapshot_hash` / `target` / `source` / `lag` / `sign` / `score` /
  `stability` / `generated_as_of` / `pipeline_version`, and `tests/test_api_boundary.py:162-177`
  asserts each one field-by-field against the report body. `mode: "realtime"` gives G.5's
  backtest-vs-live labelling its slot *before* a backtest path exists — the correct order, since
  an unlabelled ledger is untrustworthy from its first line.
- **Fail-soft is asserted, not merely written.**
  `test_ledger_append_failure_does_not_fail_analysis` points the env var at a directory to force
  the failure and confirms the run still returns.
- **The `p_value` display defect (A.4-2 / B.5) is closed.** `render_logic.fmt_p_value` returns
  `< 1e-12`, and the `1e-300` gate floor lands inside that branch.
- **The M3 DoD walkthrough is machine-enforced.** The spec does not narrate a fixture-by-fixture
  walkthrough, but `tests/test_website_frontend.py` drives all eight `mock_reports_v1.json`
  states through `render_logic`, covering null-never-zero, baseline-confidence-null,
  no-fabricated-trajectory, and exactly-one-active-lifecycle-step. That is a stronger form of
  the verification the plan asked for.
- **The deployed web build contains the audience-visible fixes** — established by ancestry
  rather than by screenshot. Both the landing copy and the noise-floor caption were introduced
  in `5a268ce`; `5a268ce` is an ancestor of the deployed `71169b2`; and
  `git diff 71169b2..HEAD -- src/nestor_delta_web/` is empty, so the deployed web layer is
  current. This closes the substance of the missing-screenshot gap. A rendered capture is still
  worth having for the demo record, but the acceptance no longer rests on it.

### J.3 M3.5 entry conditions

**1. `ledger.durable` is the next decorative field. (Highest value in this list.)**

`boundary.py:76` computes `"durable": bool(configured_path)` — true if and only if
`NESTOR_RELATIONSHIP_LEDGER_PATH` is set. It reports **configuration, not observation**. It stays
`true` if the volume unmounts, if the path becomes unwritable, or if the mount points at
ephemeral storage. And because the append path is fail-soft by design, a write failure reaches
only the logs.

G.5's premise is that a track record cannot be created retroactively. So a silent write failure
is a permanent hole in the record, during which `capabilities` continues to advertise health.

Apply the B.4 test — *what would have to change for this field to change?* Only an environment
variable. That is the same shape as hardcoded `pipeline_version` and non-gating `noise_floor`:
the third instance of the pattern, arriving one milestone after the pattern was named.

Fix: separate `ledger.configured` from an observed signal — a startup write probe plus
`ledger.last_write_ok` and `ledger.lines`. `test_capabilities_are_truthful` should then assert
the observed field rather than the environment variable it currently mirrors.

**2. The F.2 pairing rule is violated in the one place that matters most.**

`M3_VISUAL_AUDIT_SPEC.md` states that lifecycle labels must be paired with `stability`
"wherever the UI gives them visual weight". The relation detail panel complies (lifecycle track
plus a Stability metric tile); the Analyst table complies (both columns present).

But `streamlit_app.py:368-372` builds the expander label as
`source → target · lifecycle · selected/not selected` — lifecycle with no stability — and
non-selected relations render collapsed. **The collapsed list is the scan surface**: it is where
a viewer forms an impression before opening anything, and it is where `intermittent → stable`
reads exactly as F.2 warned.

Fix: add `stability` to the expander label, or remove the lifecycle label from it.

**3. `/api/v1/capabilities` response freshness.**

A fetch to the canonical `https://api-production-9849.up.railway.app/api/v1/capabilities`
returned the **pre-M3** `s10.sha256.7763cf123030` with no `ledger` object. The same endpoint
fetched moments later with a cache-busting query parameter returned the current values.

The mechanism is undiagnosed — naming a cache would already presume the cause. Appendix F used a
cache-busted fetch by convention; this round shows the convention was load-bearing rather than
fastidious. Capabilities is the discovery surface consumers are told to read instead of
hardcoding (API_BOUNDARY §5.6), and it carries `pipeline_version` — both are worthless if a stale
response can be served, and the failure is invisible precisely because the response looks
well-formed.

Fix: diagnose the mechanism, then decide a policy. Until then every verification fetch must carry
a cache-busting parameter, and that requirement belongs in the deployment doc rather than in
reviewers' habits.

**4. `EVIDENCE_GATE_CONFIG` was not reported, and it creates a second home for the prohibited
thresholds.**

`adapter.py` now passes gate thresholds explicitly:

```
EVIDENCE_GATE_CONFIG = {"alpha": 0.05, "min_stability": 0.45,
                        "max_uncertainty": 0.20, "min_sample_support": 0.50}
```

Checked against `evidence_gate.py:43-46` at both `71169b2` and `HEAD`: **identical to the
defaults.** Nothing was loosened, and making implicit configuration explicit is precisely what
G.3 asks for. `_rolling_window_size` is likewise a pure extraction of the previously inlined
`min(36, max(lag_window + 6, len(train_rows) // 3))` — same rule, no behaviour change, and now
published in the report.

Two consequences follow.

- The standing prohibition "do not loosen evidence-gate thresholds" now covers
  `adapter.py:EVIDENCE_GATE_CONFIG` as well as `evidence_gate.py`. A future change could weaken
  the gate without touching the file that carries the warning. Record the prohibition in
  `adapter.py` itself, not only in this document.
- This is the second consecutive milestone in which a change to gate-determining code was found
  by reading diffs rather than from the report. F.1 named the rule by filename and this round
  complied for that filename. **Restate the rule by scope: anything that determines a selection
  threshold is reported proactively, wherever it lives.**

### J.4 Delivered but not reported: G.3 is half-built

The report described M3.5 as holding only the denominator-ledger gap. In fact the `configuration`
block from G.3 is already implemented and shipped: `adapter.py:_configuration_block` emits
`reproducibility.rule`, `inputs` (source, train_end, lag_window, candidate_count,
train_observations, transform_declarations), `effect.score_scope = "full_train_window"`, and
`rolling_lifecycle.window_rule` with its effective value; `schema.py` adds `configuration`,
`producer`, and `pipeline_version` at the report root.

This is real progress on G.3's first obligation — *publish the effective configuration* — and it
is good work. Two qualifications:

- **It is half-delivered.** The block reaches the JSON but nothing on screen, because the
  deployed web build (`71169b2`) predates it. Extra-field tolerance is tested so nothing breaks,
  but a consumer comparing two reports still cannot see the effective configuration in the
  product.
- **G.3's second obligation is untouched.** There is still no ground-truth fixture per branch:
  all fixtures remain n=216, while `_rolling_window_size` is a live branch that a small real
  upload would take. That is the branch-boundary gap G.3 warned about, now with running code
  behind it.

### J.5 Minor

`fmt_p_value(0.0)` falls through to `"0.0000"`, because the guard is `0.0 < number < 1e-12`. The
`1e-300` floor makes this unreachable from `evidence_gate`, but an older fixture or a future
producer could still surface an exact zero — the display the fix existed to prevent. One-line
guard.

### J.6 Carried into M3.5

- Denominator-ledger design gap (deferred by instruction; correctly not allowed to block this
  deployment).
- H.4: a relation whose `stability` is below the gate may not be labelled `birth`.
- I.1 P0a over-differencing diagnostic; I.3 lag-profile axis.
- G.3 fixture-per-branch (§J.4).
- A rendered post-deploy capture of the `ok` screen, for the demo record rather than for
  acceptance.

---

## Appendix K — Documentation repair and the review that corrected it

Between M3 acceptance and any M3.5/M4 work, the governing documents were found to have drifted
from the shipped system and were repaired. This appendix records what changed and, more usefully,
the three judgements the review overturned.

### K.1 What had drifted

| Document | Drift |
|---|---|
| `API_BOUNDARY_V1.md` (project copy) | two milestones behind the repo copy, including a changed governing principle (P2) |
| `API_BOUNDARY_V1.md` (repo copy) | Status claimed "not yet implemented" long after M2; §1 example was the same hand-authored placeholder string B.3 had already caught being copied into code as a live value; §2.8 still showed the pre-B.3 preset shape |
| `WEBSITE_CONTRACT_W0.md` | product framing still listed the noise floor as a test relationships must survive — the claim decision B removed and M3 fixed *in the landing copy that quoted it*, but not at the source |
| `WEBSITE_BACKEND_CONTRACT.md` | asserted that capabilities prevents a deployment from "silently pretending" an ephemeral ledger is durable, which the code does not do |
| `HANDOFF.md` | four milestones stale: no public deployment, 132 tests, an already-made next decision — in the file its own resume checklist opens with |

W0 was moved into `docs/` so it is line-reviewable and version-controlled; it and the project copy
must now be kept byte-identical, as `API_BOUNDARY_V1.md` already is.

### K.2 The pattern, stated correctly

Every milestone has been accepted, and every milestone has also produced one new instance of the
B.4 defect class — a field or sentence that reads as authoritative while nothing is wired to it.
`effect.score` (M0), `pipeline_version` (M1), the noise-floor rendering (M2/M3), `ledger.durable`
(M3). Speed is not the variable: M0 was the least rushed milestone and produced the most serious
instance.

What is the variable is that **nothing in the acceptance criteria catches this class.** Of the
four, only `effect.score` was caught by a test — and only because a fixture existed whose answer
was known by construction. The other three were caught by a person reading diffs unprompted.

`WEBSITE_BACKEND_CONTRACT.md` was the first instance to appear in the *governing documents* rather
than in code, which is worse, because CI validates schema and cannot validate prose.

### K.3 Three judgements the review overturned

Recorded because each was wrong in an instructive way.

**1. "Run the suite with `unittest discover`."** That collects 145 and silently omits the 26
pytest-style ground-truth functions — the only tests that check whether the detector detects. The
full command is `PYTHONPATH=src:tests/ground_truth .venv/bin/python -m pytest tests -q`, giving
171. A test command that omits the ground-truth suite is the most expensive possible instruction
to leave in a handoff, given §A.2.

**2. "Code plus tests is the authority when documents disagree."** Rejected. Code and its tests
can encode the same mistake together and stay green indefinitely — 132 tests passed while
`effect.score` overstated the headline number by 14%. Authority is split by the kind of question
being asked, recorded as `API_BOUNDARY_V1.md` §4.4: machine structure to Pydantic plus the
committed schema; algorithmic truth to the frozen rules plus ground-truth fixtures; semantics and
UI obligations to the accepted contracts; current deployment fact to the deployment itself.

**3. "Changing a metadata string would fire a false alarm in `pipeline_version`."** Rejected, and
this was the sharpest correction. `pipeline_version` asserts that the implementation producing a
Report is identical — not that only numerical algorithms move it. The string is Report content, so
changing it changes the Report's bytes and its stated semantics, and a new version number is an
accurate statement about that. Deferring the fix to ride along with a "more algorithmic" change
would have (a) left a known live contract contradiction standing, (b) hidden two independent
changes inside one version movement, weakening attribution, and (c) accommodated a misreading of
the field rather than correcting it.

### K.4 The reproducibility correction

P2 and §2.7 had contradicted each other since M3: P2 listed `effective_configuration` as a fourth
term of `f`, the idempotency key listed three. Resolved in favour of three, because configuration
is a published *result* of the other terms, not an independent input:

```
effective_configuration = g(snapshot, analysis_params, pipeline_version)
report                  = f(snapshot, analysis_params, pipeline_version)
```

Any override a user can set is an analysis param and belongs in the second term. If a value ever
influences the outcome without being derivable from those three, that is a P2 violation, not a
reason to add a fourth term. `M3_ARCHITECTURE_PRINCIPLES.md` and the in-Report
`configuration.reproducibility.rule` string were brought into line.

**Reproducibility metadata corrected from a four-term to a three-term dependency statement.
Analytical calculations, thresholds, and outputs are unchanged; S-GT-1 `effect.score` remains
`0.5844220533473201`.** `pipeline_version` moves `s10.sha256.77f014d78885` →
`s10.sha256.3665b88553ad`. Existing archived fixtures keep the old value, correctly: they are
genuine historical evidence of what the older build produced.

### K.5 Still open after the repair

- **Capabilities response freshness.** A fetch to the canonical URL returned a superseded
  `pipeline_version` with the `ledger` block absent, while the same endpoint with a cache-busting
  parameter returned current values moments apart. The mechanism is undiagnosed — naming a cache
  would already presume the cause. No `Cache-Control` policy is prescribed; every verification
  fetch must carry a cache-busting parameter until it is understood.
- **The J.3-1 ledger signal.** The contract now describes the real limitation instead of claiming
  a guarantee, but `durable` still reports only that a non-default path was configured.
- **A standing acceptance item** — for every field a surface renders and every guarantee a
  document asserts, name what would have to change for it to be false — proposed, not yet agreed.
- **Whether M3.5 runs as a milestone at all**, or is folded into M4 and M5 keeping only the two
  safety items. Proposed, not yet agreed.

---

## Appendix L — Source revision: a build-identity mechanism, and the review that made it honest

Closes the gap Appendix F and §J named but could not fix: `pipeline_version` detects a stale
**analysis-and-adapter** build and nothing else, so a stale API or web deployment had no signal
at all. The mechanism now exists. Recorded here in full because the first attempt was wrong in
four ways, and the four are more instructive than the result.

### L.1 What the mechanism is

`source_revision` — the commit a running process was built from — reported by
`/api/v1/capabilities`, `/health`, and the web sidebar. Resolution order:
`RAILWAY_GIT_COMMIT_SHA` → `NESTOR_BUILD_SHA` → local `git rev-parse` → `"unknown"`. Candidates
are accepted only as 7–40 hex characters after stripping; blank and malformed values are skipped
rather than passed through. Platform value first, so a stale hand-set variable can never shadow
an authoritative one.

Deliberately outside the `pipeline_version` hash, and verified so: the hash was recomputed after
the change and is unchanged at `s10.sha256.3665b88553ad`. Adding build identity produced no
version movement — which is the §1.1 boundary working as designed rather than as asserted.

### L.2 The four corrections

**1. It would have reported `"unknown"` in production, and only production would have said so.**
The first version resolved from `NESTOR_BUILD_SHA`, `RAILWAY_GIT_COMMIT_SHA`, then `git`. Direct
inspection of both live services found none of the three available: neither variable is set, the
deploy is a CLI upload so Railway reports `repo: null` and injects no commit variable, and the
image excludes `.git` via `.dockerignore` / `.railwayignore`. Every source was unavailable.

A field whose only live value is `"unknown"` is the B.4 defect class again, in the very
mechanism built to detect a related one. The fix is `scripts/deploy-railway.sh`: a single deploy
entry point that refuses a dirty tree, stamps `NESTOR_BUILD_SHA` with the current commit, deploys
immediately, and verifies. The stamping and the deploy must not be separated, and the variable
must never be set by hand in a dashboard — a variable that survives the next deploy is a
hardcoded version string, exactly the defect §B.3 recorded `pipeline_version` having had.

**2. It was named for something it cannot prove.** `service_build_version` claims deployment
identity. What the value actually is, is a source revision: locally it read `c1ca10b13077`, a git
SHA, and it changes with every commit. Two tiers reporting the same value were built from the
same commit — they were not necessarily deployed together, and API and web are independent
deployments that can drift while agreeing here.

Renamed to `source_revision` in the field, the caption, and the documentation. A true deployment
identity remains **unavailable**: CLI-upload deploys expose no platform deployment variable. That
absence is now recorded rather than papered over by a name.

**3. Its parsing was not honest.** Measured on the first version: `NESTOR_BUILD_SHA="   "`
resolved to `""` — and worse, a blank value shadowed a valid platform SHA, because presence was
tested rather than validity. `"not-a-sha"` was passed straight through. Now every candidate is
stripped, lowercased, and matched against `\A[0-9a-f]{7,40}\Z`; a failing candidate is skipped
and resolution continues to the next source, including for `git` output (`fatal: not a
repository` no longer becomes a revision).

**4. The panel consumed the staleness it was built to reveal.** The sidebar reads `/health`, and
`api_client.health()` fetched a fixed URL with no cache-buster while stale responses from the
canonical capabilities URL were an open, undiagnosed finding (§J.3-3). A health panel served from
that same staleness could confirm a deploy that never happened. `/health` is now cache-busted per
call.

### L.3 Two decisions taken during the fix

- **The rename** (L.2-2) extended beyond the caption the review asked for, to the JSON field and
  the contract. The field was unshipped, so the change was free; a name that overstates is the
  defect class this project exists to refuse.
- **`pytest` was an undeclared dependency.** `requirements-lock.txt` stated that the core
  analysis "and its test suite use only the Python standard library". That is false for the
  complete suite: the 26 ground-truth tests are pytest-collected plain functions, and pytest was
  installed in the working virtualenv while declared nowhere. Added as
  `[project.optional-dependencies] dev = ["pytest>=7"]` (the `pythonpath` ini option requires 7),
  and the claim in `requirements-lock.txt` corrected.

### L.4 The test-command trap, closed at the root

`unittest discover -s tests` collects 145 and cannot collect the 26 ground-truth tests at all —
they are plain functions, not `unittest.TestCase`. Those 26 are the only tests that check whether
the detector detects (§A.2). The trap existed because the correct invocation required remembering
an environment prefix.

`pyproject.toml` now sets `pythonpath = ["src", "tests/ground_truth"]` and `testpaths =
["tests"]`, so a bare `pytest` collects all 171 and there is no prefix to forget. This does
**not** change `unittest discover`, and the three documents that recommended it — `README.md`,
`REPRODUCIBILITY.md`, `docs/WEBSITE_FRONTEND_RUN.md` — were corrected to `pytest` with the
145-vs-171 distinction stated.

> The counts in the paragraph above are the values at the time of this record and are left
> as written. The suite has since grown to **179**; `unittest discover` still collects 145.
> Q1 additionally found that a bare `pytest` needed five undeclared packages before it could
> reach those tests at all — see `docs/REMEDIATION_Q_V1.md`.

Noted, not fixed: five of eighteen test modules insert `src` into `sys.path` themselves while the
rest rely on ambient path, and a bare `import nestor_delta` from the repository root fails. The
pyproject setting makes the path uniform under pytest; the per-file hacks remain.

### L.5 What is verified, and what is not

Verified: `tests/test_build_identity.py` passes — 5 tests carrying 13 resolution cases run against
**both** implementations, with an explicit drift assertion (the web package may not import
anything named `nestor_delta*`, so the helper is duplicated; the test module is not under that
restriction and drives both copies through one table). All eight changed Python files compile.
The frontend-isolation assertion was reproduced with no violation. `pipeline_version` recomputed
and unchanged.

Not verified at the time of writing: the full suite. `test_api_boundary.py` gained a `/health`
versus `capabilities` cross-check that needs FastAPI, and `test_website_frontend.py` covers the
two web files that changed. Both require the project virtualenv, which is macOS-built and cannot
run in the review environment. `python -m pytest -q` must pass before these changes are committed.

Also unverified: the Railway CLI flag syntax inside `scripts/deploy-railway.sh`. It differs
between major CLI versions and could not be checked without network access. The script says so
and instructs the reader to correct the flags there rather than working around them by hand.

### L.6 Still open after this round

- **Capabilities response freshness** (§J.3-3) — still undiagnosed. Two `curl -sI` calls against
  the canonical and cache-busted URLs will settle whether it is a cache; no `Cache-Control`
  policy is prescribed until it does. Until then every verification fetch carries a cache-buster.
- **`ledger.durable`** (§J.3-1) — the contract now describes the real limitation, but the signal
  still reports only that a non-default path was configured.
- **A true deployment identity** — not merely a source revision. Unavailable while deploys are
  CLI uploads.
- The standing acceptance item (§K.5) and whether M3.5 runs as a milestone at all (§K.5) remain
  proposed rather than agreed.
