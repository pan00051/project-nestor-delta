# HANDOFF · Nestor Delta

This file is the short operational handoff. Stable scope belongs in
`BLUEPRINT.md`; frozen S7-S10 acceptance rules belong in `S7-S10的规则.md`;
implementation details belong in code, tests, and `docs/`.

The version-controlled milestone plan and analysis contract live at
`docs/DEMO_MILESTONES_V1.md` and `docs/WEBSITE_CONTRACT_W0.md`. Their Claude
project copies are byte-identical mirrors. Read the milestone plan before
planning work; this file only states where the code currently stands.

Historical M3 acceptance and deployment baseline: `ad77fd3`. Current source and
deployment identity are stated separately below; do not infer the current HEAD
from this file.

## Current State

- Branch `main`. M3 acceptance facts below describe `ad77fd3`; the current
  source revision includes the documentation and reproducibility-metadata
  correction recorded in `docs/DEMO_MILESTONES_V1.md` Appendix K.
- Milestones M0-M3 accepted. M3.5 and M4 are not started; the milestone
  revision itself is under review (see "Next Decision").
- Analysis pipeline S1-S10: complete and independently reviewed.
- Website W0-W5: complete.
- Report contract: `delta.report.v1`. M2 added a content-derived
  `pipeline_version`; M3 added `producer` and a `configuration` block that
  publishes the effective gate terms, the rolling-window rule, the diagnostic
  role of the noise floor, and the transform/sample inputs.
- `pipeline_version` is a SHA-256 over `versioning.py`, `adapter.py`, and every
  module under `src/nestor_delta/`, rendered `s10.sha256.<12 hex>`. It is never
  hand-written. Current value: `s10.sha256.3665b88553ad` (was
  `s10.sha256.77f014d78885` before the reproducibility-metadata correction; no
  calculation changed).
- **What that field covers, and what it does not.** It identifies the
  implementation that produced a Report. It moves for any change to the hashed
  files, including a corrected metadata string — that is correct, not noise, and
  a moved version does not by itself mean numbers changed. The API layer
  (`app.py`, `boundary.py`, `schema.py`, `errors.py`, `eurostat.py`) and the web
  build are **outside** the hash and must not be folded into it. A current
  `pipeline_version` therefore proves the analysis and adapter build is current;
  it is not evidence that the API or web deployment is.
- **`source_revision`** covers that second question, on both tiers:
  `capabilities`, `/health`, and the web sidebar. It is a *source revision*, not
  a deployment identity — equal values mean same commit, not same deployment,
  and API and web deploy independently. A true deployment identity is
  unavailable: CLI-upload deploys expose no platform commit variable.
  `"unknown"` in production is a defect, not a default. See
  `docs/API_BOUNDARY_V1.md` §1.1.
- **Deploy only through `scripts/deploy-railway.sh <service> [health-url]`.** It
  refuses a dirty tree, stamps `NESTOR_BUILD_SHA` with the current commit, and
  deploys immediately, so the value cannot outlive the code it names. Never set
  that variable by hand in the Railway dashboard. Sequence and gate below.

### Deploy sequence

One service at a time, API first, only through the script.

1. `scripts/deploy-railway.sh api <api-url>/health`
2. **The gate for the second deploy is that the first one *verified*, not that
   it *succeeded*.** `source_revision` must equal the commit you deployed. If it
   comes back `unknown`, the stamped variable never reached the process — stop
   there and fix that. Deploying the second service at that point only doubles a
   surface that cannot say what it is.
3. `scripts/deploy-railway.sh web <web-url>` — web exposes no `/health` of its
   own; read the sidebar `Source revision` caption instead.

**Why API first.** The web sidebar reads `source_revision` from the API's
`/health`. Deploying web first shows `api unknown` until the API catches up:
correct behaviour, but a confusing signal to start from.

**Both tiers should carry the same commit unless a split is intended.** The
likeliest reason to edit between the two deploys is correcting the Railway CLI
flags inside the script — and that produces a new commit. If it happens,
re-deploy the API from the corrected commit before deploying web, rather than
letting the two tiers drift apart by accident.

**Every verification fetch carries a cache-buster.** `/api/v1/capabilities` has
been observed returning stale responses from its canonical URL and the mechanism
is still undiagnosed; an uncached check could confirm a deploy that never
happened.
- API: `/api/v1/runs`, `/api/v1/runs/{run_id}`, `/api/v1/capabilities`,
  `/api/v1/audit`, `/api/v1/snapshot`, plus `/analyze`, `/audit`, `/snapshot`
  as retained unversioned aliases, plus `/health` and `/schema/report`.
- Frontend: Streamlit, HTTP only. `src/nestor_delta_web/` holds zero imports of
  `nestor_delta` or `nestor_delta_service`; there is no direct-import path to
  fall back on.
- Data sources: bundled cases, aligned CSV upload, exact Eurostat
  dataset/filter definitions. The demo path runs on a frozen snapshot; live
  Eurostat fetch works from the deployment but is a bonus, not the script.
- Selected-relation ledger: append-only JSONL written at the API Run boundary
  for completed runs with selected relations. Fail-soft by design — a write
  failure is logged and never fails the request.

### Deployment

- Live on Railway, two services, cross-origin:
  `api-production-9849.up.railway.app` and `web-production-31a89.up.railway.app`.
- `scripts/start-railway-service.sh` branches on `RAILWAY_SERVICE_NAME`.
  **The API runs with `--workers 1` deliberately.** `RunStore` is a
  process-local singleton; a second worker makes `GET /api/v1/runs/{id}` return
  404 non-deterministically. Do not add workers until the store is shared.
- Serverless sleep is **disabled on both services on purpose** for the demo
  period. Sleeping the API destroys `RunStore`, which would silently reduce
  `run_retention` from `max_runs: 100` to "until the next idle window".
- A persistent volume is mounted at `/data` and
  `NESTOR_RELATIONSHIP_LEDGER_PATH=/data/relationship_ledger.jsonl`.
- Python: production is pinned to 3.10.14 by the Dockerfile. The package
  declares `requires-python = ">=3.9"` and the checked-in `.venv` is 3.9.6,
  on which the full suite passes. The declared range and the deployment pin
  are both accurate; they are simply not the same number.

### Last recorded acceptance

M3, at `ad77fd3`: **171 passed in 37.42s** locally, re-verified during the
documentation review. 26 ground-truth tests passed against the deployment.
`effect.score` on the S-GT-1 control is `0.5844220533473201`, unchanged across
M0 through M3.

Run the suite with the full command below. `unittest discover` alone collects
145 and silently omits the 26 pytest-style ground-truth functions, which are
the only tests that check whether the detector actually detects:

```
PYTHONPATH=src:tests/ground_truth .venv/bin/python -m pytest tests -q
```

### Known open defects

Full detail and rationale live in `docs/DEMO_MILESTONES_V1.md` Appendix J.

1. `capabilities.ledger.durable` reports only that a non-default path was
   configured. It does not verify that the path is writable or persistent, and
   writes are fail-soft, so a broken ledger reports healthy while losing a
   record that cannot be rebuilt later. The contract now states this limitation
   rather than the guarantee it used to claim; the signal itself is still to be
   fixed.
2. The relation expander label shows a lifecycle state without its `stability`
   value, which the visual spec forbids. The collapsed list is the scan surface.
3. A fetch to the canonical `/api/v1/capabilities` URL returned a superseded
   `pipeline_version` with the `ledger` block absent, while the same endpoint
   with a cache-busting parameter returned current values moments apart. The
   mechanism is undiagnosed — do not assume a cache. Every verification fetch
   must carry a cache-busting parameter until it is.
4. `configuration` reaches the report body but nothing renders it; the deployed
   web build predates it.
5. All ground-truth fixtures are n=216, so the rolling-window branch has no
   boundary fixture.

## Non-Negotiable Boundaries

1. `src/nestor_delta/` remains the algorithmic source of truth. Do not duplicate
   S1-S10 calculations in FastAPI, SQL, or the frontend.
2. S9 stability and lifecycle must consume the S7 transformed relation
   trajectory, never legacy level Pearson scoring.
3. S10 selection may use relationship evidence only. Prediction or validation
   error must not feed back into selection.
4. The frontend displays Report JSON values and explicit empty/error states; it
   must not infer missing intervals, confidence, trajectories, or conclusions.
5. Core analysis reads frozen snapshots. A future SQL layer may manage intake
   and audit data, but must export a hashed immutable snapshot before analysis.
6. Existing frozen S0-S10 reports are historical evidence and are not rewritten
   to make newer results look cleaner.
7. **Evidence-gate thresholds may not be loosened.** They now live in two
   places: the defaults in `src/nestor_delta/evidence_gate.py` and
   `EVIDENCE_GATE_CONFIG` in `src/nestor_delta_service/adapter.py`. The two
   must be changed together and stay in sync, and any change is reported
   proactively. Justification is that both controls still give their own
   correct answer: S-GT-1 must still select the true relation and recover its
   lag and sign; S-GT-2 must still return `baseline_only` with
   `selected_count: 0`. Record before/after for both. They are a positive and a
   negative control and are not expected to move in the same direction.
8. `noise_floor` is a diagnostic comparison scale and gates nothing. No surface
   may render it as a threshold, a floor beneath a score, or a pass/fail badge.

## Next Decision

**Under review — do not start implementation work until it closes.** The
milestone documents had drifted from the shipped system, and the repair pass is
finished and awaiting cross-review. Three revisions to how milestones are
accepted are proposed but not agreed:

1. **Open.** Add a standing acceptance item — for every field a surface
   renders, and every guarantee a document asserts, name what would have to
   change for it to be false. If nothing would, it is decoration.
2. **Decided.** Authority is split by the kind of question being asked; see
   `docs/API_BOUNDARY_V1.md` §4.4. "Code plus tests wins" was considered and
   rejected: code and its tests can encode the same mistake together, as they
   did for 132 green tests while `effect.score` was wrong.
3. **Open.** Fold M3.5 into M4 and M5 rather than running it as a milestone,
   keeping only the two items that are safety rather than fidelity: the ledger
   durability signal and capabilities response freshness.

Once that closes, the outstanding milestone work is M4 (charts plus the CSV
human-acceptance checklist — the only Demo DoD item not yet reachable) and M5
(rehearsal and freeze).

## Resume Checklist

1. Read `docs/DEMO_MILESTONES_V1.md`, then
   `BLUEPRINT.md` and this file.
2. Read `docs/WEBSITE_BACKEND_CONTRACT.md` for API work or
   `S7-S10的规则.md` for algorithm work.
3. Check `git status --short --branch` before editing.
4. Before completion, run the full suite — not `unittest discover`, which
   omits the ground-truth tests:

   ```
   PYTHONPATH=src:tests/ground_truth .venv/bin/python -m pytest tests -q
   ```
5. Update this handoff only when current state, boundaries, or the next decision
   changes.

## Important References

- Milestone plan and acceptance records: `docs/DEMO_MILESTONES_V1.md`
- Insight⇄Delta boundary: `docs/API_BOUNDARY_V1.md`
- Analysis contract: `docs/WEBSITE_CONTRACT_W0.md`
- Report contract: `docs/WEBSITE_BACKEND_CONTRACT.md`
- Visual state spec: `docs/M3_VISUAL_AUDIT_SPEC.md`
- Architecture principles: `docs/M3_ARCHITECTURE_PRINCIPLES.md`
- Deployment record: `docs/M2_DEPLOYMENT.md`
- Canonical report states: `docs/mock_reports_v1.json`
- Website run guide: `docs/WEBSITE_FRONTEND_RUN.md`
- Reproduction commands: `REPRODUCIBILITY.md`

Historical implementation detail remains available in Git history through commit
`9c8217f`; it is intentionally not duplicated in this current-state handoff.
