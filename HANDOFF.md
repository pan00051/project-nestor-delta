# HANDOFF · Nestor Delta

This file is the short operational handoff. Stable scope belongs in
`BLUEPRINT.md`; frozen S7-S10 acceptance rules belong in `S7-S10的规则.md`;
implementation details belong in code, tests, and `docs/`.

## Current State

- Branch: `main`.
- Analysis pipeline S1-S10: complete and independently reviewed.
- Website W0-W5: complete locally.
- Report contract: `delta.report.v1`.
- API: synchronous `/snapshot`, `/audit`, and `/analyze` plus health/schema
  endpoints.
- Frontend: Streamlit, connected to FastAPI over HTTP only.
- Data sources: bundled cases, aligned CSV upload, and exact Eurostat
  dataset/filter definitions.
- Last recorded acceptance: 132 repository tests and 22 frontend tests passed;
  bundled Spain and the verified Eurostat preset passed live end-to-end checks.

No public deployment, report persistence, accounts, share links, PDF export, or
generic Eurostat catalog search is implemented.

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

## Next Decision

Choose exactly one next sprint before implementation:

- **Deployment:** Railway FastAPI plus Streamlit Cloud, environment variables,
  health checks, and online smoke tests. No database.
- **Eurostat discovery:** define a constrained catalog/filter API, cache policy,
  and error contract. Preserve the current exact-definition and snapshot path.

Report history, sharing, accounts, and database-backed jobs remain separate
future decisions.

## Resume Checklist

1. Read `BLUEPRINT.md` and this file.
2. Read `docs/WEBSITE_BACKEND_CONTRACT.md` for API work or
   `S7-S10的规则.md` for algorithm work.
3. Check `git status --short --branch` before editing.
4. Run `python -m unittest discover -s tests` before completion.
5. Update this handoff only when current state, boundaries, or the next decision
   changes.

## Important References

- Website run guide: `docs/WEBSITE_FRONTEND_RUN.md`
- Report contract: `docs/WEBSITE_BACKEND_CONTRACT.md`
- Canonical report states: `docs/mock_reports_v1.json`
- W5 acceptance record: `docs/W5_ACCEPTANCE.md`
- Reproduction commands: `REPRODUCIBILITY.md`

Historical implementation detail remains available in Git history through commit
`9c8217f`; it is intentionally not duplicated in this current-state handoff.
