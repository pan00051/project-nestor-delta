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
- Product direction: non-commercial portfolio and personal-analysis system.
  SaaS-like capabilities are lightweight access/display features only
  (invite-gated access, saved reports, shareable read-only outputs). Billing,
  To B / To C growth, organization workspaces, and enterprise tenancy are not
  goals.
- SDD direction: development-time algorithm exploration is allowed to move fast.
  Full frozen verification is required for public claims, milestone acceptance,
  deployment acceptance, and resume/portfolio language, not for every temporary
  debugging pass.
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
  404 non-deterministically. Ledger observation, TTL, line count, append result,
  and locking are also process-local, so multiple workers can make health
  oscillate and cannot coordinate JSONL appends. Do not add workers until both
  RunStore and ledger observation/write coordination use shared, process-safe
  storage.
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

Current deployed API source revision `c6afbb581ff7`: **182 passed** locally.
API `/health` and `/api/v1/capabilities` report that revision with
`Cache-Control: no-store`. The web remains on `01a9e6ca2637` because no web
source changed in the intervening commits.

**Q3 response-freshness evidence, 2026-08-28 09:11-09:16 UTC.** Codex queried
the production API from the local workspace against both canonical and
cache-busted URLs. Canonical `/health` returned HTTP/2 200 with:
`content-type: application/json`, `server: railway-hikari`,
`x-railway-request-id: kaeVcSAdRSe-awrr0_TJvA`, `x-hikari-trace: cdg1.e9jw`,
`x-railway-edge: cdg1`, and body
`{"status":"ok","schema_version":"delta.report.v1","source_revision":"01a9e6ca2637"}`.
Cache-busted `/health?cb=q3-codex-20260828-2` returned the same body and headers
shape with request id `bfjJZi95TiOlEegF6WHkDg`. Canonical
`/api/v1/capabilities` returned HTTP/2 200 with `server: railway-hikari`,
`x-railway-request-id: 9w5TiDEYRW-W2kWVn6XIxQ`, `x-hikari-trace: cdg1.e9jw`,
`x-railway-edge: cdg1`, `vary: accept-encoding`, no `Age`, no `ETag`, and no
`Cache-Control`; cache-busted
`/api/v1/capabilities?cb=q3-codex-20260828-1` returned the same body and headers
shape with request id `SwDMa4gtSYq0hFexwUFZXw`. Ten consecutive canonical
`/api/v1/capabilities` samples all returned
`pipeline_version=s10.sha256.3665b88553ad`, `source_revision=01a9e6ca2637`, and
a present `ledger` block. Result: the earlier stale response was not reproduced,
and no new/old process jump was observed. F1 still applies because provenance
endpoints had no explicit cache policy before this fix.

**Q4 ledger signal repair.** `capabilities.ledger.durable` no longer mirrors
whether `NESTOR_RELATIONSHIP_LEDGER_PATH` is set. The ledger block now separates
deployment intent from observation: `configured`, `writable`, `last_write_ok`,
`lines`, `path`, and `write_probe_error`, with `durable` true only when a
non-default path is configured and a same-directory write/read/cleanup probe
passes. `/health` returns the same ledger block so probe failure is visible from
the health surface. Real append failures still do not fail analysis requests;
they flip `last_write_ok` false and continue logging fail-soft. Boundary: this
proves current-process write health, not cross-restart persistence. An external
review caught that the first implementation probed and scanned the complete
append-only file on every public health/discovery request. The observation is
now cached for 60 seconds, the line count is initialized once per path or path
recovery, and real appends update it incrementally. Repeated `/health` and
`capabilities` requests inside the TTL perform no ledger I/O. Railway volume
persistence must still be verified out of band after deploy.

`ledger.observed_at` reports when the cached observation was last refreshed by
a probe or real append; cache hits preserve it, so callers can see the bounded
staleness directly. Two known operational limits remain deliberately unchanged
for the deployment freeze: external file changes can make incremental `lines`
drift until restart/recovery, and a crash or forced kill can leave a `.probe-*`
file. Neither affects Report content or the Q3 deployment-window criteria.

**Q4 hot-path follow-up acceptance, 2026-08-28.** The API boundary suite is
`14 passed`; the complete required command `.venv/bin/python -m pytest -q` is
`182 passed` (the prior 179 plus three cache/TTL regressions). A one-second
read-only smoke run of `scripts/sample-q3-deploy-window.py` against production
recorded both canonical and cache-busted responses with revision
`01a9e6ca2637`, ledger present, and upstream zone `railway/us-west2`. Their
`x-hikari-trace` values differed (`hkg1.aebn,hnd1.df23` versus
`hkg1.aebn,hnd1.4cm0`) despite the same deployed revision, reinforcing that the
field is not an application-instance identity. This was a sampler smoke test,
not the time-limited deployment experiment. No deployment occurred; D5 remains
reserved for the next API cutover.

**Q3 deployment-window evidence, 2026-08-29.** API deployment
`acf3549e-f497-4cee-8da4-21ce7b8c7d86` moved production from
`01a9e6ca2637` to `c6afbb581ff7`. The sampler captured 127 requests: 126 HTTP
200 and one canonical 502 during cutover. After the first new response, all 66
successful canonical/cache-busted responses stayed on the new revision, exposed
`Cache-Control: no-store`, and included ledger plus `ledger_observed_at`; no old
revision returned. Railway also showed that setting `NESTOR_BUILD_SHA` creates
an automatic prior-source redeploy before the CLI upload; it was removed before
serving in this first run. Evidence:
`docs/evidence/Q3_DEPLOYMENT_WINDOW_2026-08-29.md` and the adjacent raw JSONL.

**Q3 diagnosis, 2026-08-29.** A controlled follow-up set
`NESTOR_BUILD_SHA=deadbeef3333` without uploading source. Variable-triggered
redeploy `cfa0b9bf-ca81-4047-8a51-547b2292f500` then served 48 successful
public capabilities requests over about 74 seconds. Restore redeploy
`93139bad-ddf5-4d38-851d-7e67feec4015` returned production to
`c6afbb581ff7`, followed by 50 stable successful responses. This confirms the
deployment race capable of serving prior code under the new revision stamp;
the original historical request cannot be tied to a deployment ID after the
fact, so that final attribution remains a high-confidence inference. Q3 is
diagnosed; deploy-script remediation is still required before the next source
deploy and was deliberately not included in this experiment. Evidence:
`docs/evidence/Q3_VARIABLE_REDEPLOY_2026-08-29.md` and adjacent raw JSONL.

Post-deploy health and capabilities both reported revision `c6afbb581ff7`,
`Cache-Control: no-store`, and a configured/durable/writable ledger at
`/data/relationship_ledger.jsonl`; bundled-case audit returned HTTP 200 with
`ok_to_analyze`. The local required suite was `182 passed`. No web source had
changed since the prior deployed revision, so the web service was not redeployed.

**Q1 (dependency declaration) changes what that number costs to reproduce.** The
179 figure was previously only reachable on a machine that had also installed
the `web` extra, because `streamlit` pulls `numpy` and `pandas` in
transitively - an accident of the environment, not a declaration. On a clean
`[dev]`-only install the suite reported `1 failed, 178 passed`, and before
`jsonschema`/`fastapi`/`httpx` were declared it did not reach assertions at all.
`[dev]` now declares all six, and Q1.1 records the required build backend plus
pip >=21.3 floor; the documented reproduction yields `179 passed` in a fresh
venv with no `PYTHONPATH` set. No algorithm, threshold, fixture, or output
changed, so `pipeline_version` is unmoved.

Historical M3, at `ad77fd3`: **171 passed in 37.42s** locally, re-verified
during the documentation review. 26 ground-truth tests passed against the
deployment. `effect.score` on the S-GT-1 control is `0.5844220533473201`,
unchanged across M0 through M3.

Run the suite with the full command below. `unittest discover` alone collects
145 and silently omits the 26 pytest-style ground-truth functions, which are
the only tests that check whether the detector actually detects:

```
PYTHONPATH=src:tests/ground_truth .venv/bin/python -m pytest tests -q
```

### Known open defects

Full detail and rationale live in `docs/DEMO_MILESTONES_V1.md` Appendix J.

1. A historical fetch to the canonical `/api/v1/capabilities` URL returned a superseded
   `pipeline_version` with the `ledger` block absent, while the same endpoint
   with a cache-busting parameter returned current values moments apart. The
   mechanism is not fully diagnosed — do not assume a cache. On 2026-08-28,
   Codex could not reproduce the stale body in ten canonical samples and saw no
   new/old process jump. F1 now gives `/health` and `/api/v1/capabilities`
   `Cache-Control: no-store`, but every verification fetch must keep carrying a
   cache-busting parameter until the deployed service is rechecked. The next API
   deploy is a time-limited diagnostic window: start
   `scripts/sample-q3-deploy-window.py` before the deploy action and keep it
   running through cutover. Do not deploy first and reconstruct the evidence
   afterward. Matching `x-hikari-trace` values are routing evidence, not proof
   of one application instance.
2. All ground-truth fixtures are n=216, so the rolling-window branch has no
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
5. Core analysis reads frozen snapshots for claims and accepted reports. Future
   live-data intake may be used for personal analysis and exploration, but any
   live result used as public evidence must first become a hashed immutable
   snapshot with source, timestamp, parameters, and version recorded.
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

Direction reset: make Delta's practical value stronger than its narrative
value. The next implementation decision should choose between:

1. A lightweight invite-gated portfolio access layer.
2. Personal-analysis/report-history persistence.
3. Live-data intake for exploratory value discovery, with a frozen-snapshot path
   before any result becomes public evidence.
4. M4 demo fidelity work: four-state charts plus the CSV human-acceptance
   checklist.

Do not default to billing, To B / To C positioning, organization workspaces,
enterprise tenancy, or a complete SaaS account system.

**Q series — audited defects, tracked separately.** See
`docs/REMEDIATION_Q_V1.md`. Q1 (test dependency declaration) and Q2 (the
reliability-is-not-veracity wording boundary) are closed with evidence. Q3
(`capabilities` staleness) is diagnosed as a variable-triggered prior-source
redeploy race, with script remediation pending; Q4 (`ledger.durable`) is closed.
Q5 is the invite-gate above, specified small on
purpose. Q6 (no ground-truth fixture on either side of the rolling-window
boundary) is the recurrence condition for the `effect.score` class of failure
and is worth more than it looks. Q7 is the live-intake frozen-snapshot path,
deliberately after M5.

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
- Audited defects and remediation milestones: `docs/REMEDIATION_Q_V1.md`
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
