# Sprint W4 — Frontend Binding & End-to-End State Acceptance

Baseline commit: `7eb555d`. Frontend package: `src/nestor_delta_web/`
(Streamlit + pure `render_logic` + HTTP `api_client`). No `nestor_delta` import,
no analytic recomputation.

## Delivered
- `render_logic.py` — Streamlit-free rendering decisions (state classification,
  null-safe formatting, lifecycle badges, evaluation/trajectory guards, audit +
  transform-conflict logic, error/snapshot extraction).
- `api_client.py` — server-side HTTP to `DELTA_API_BASE_URL` (default
  `http://localhost:8000`), uniform `(status, body, transport)` result with
  timeout / unreachable / malformed sentinels.
- `presets.py` — bundled cases + one verified Eurostat preset (`ei_bssi_m_r2`).
  No fabricated catalog/search.
- `streamlit_app.py` — three data sources (bundled / upload / Eurostat), flow
  snapshot → audit → transform declaration → analyze → report, all states.
- `tests/test_website_frontend.py`, `requirements-web.txt`,
  `docs/WEBSITE_FRONTEND_RUN.md`.

## Test results
- `tests.test_website_frontend`: **18 passed**.
- Full suite `unittest discover`: **128 passed**.
- Data-layer end-to-end smoke (adapter → render_logic), bundled Spain retail:
  - `/audit` → `audit_ok`, axis 216/216 continuous, 2 persistence flags, no conflict.
  - `/analyze` → `report_baseline`, 0 selected, confidence **null → "insufficient /
    not evaluated"** (not 0), no evaluation interval fabricated, no fake trajectory.
  - unknown case → `404 not_found` / `case_not_found`.
  - persistent + `none` → `422 validation_error` / `high_persistence_requires_transform`.

## Acceptance checklist
1. Canonical states covered from `docs/mock_reports_v1.json` — **pass** (test).
2. `baseline_only` is a success view, not an error — **pass** (test + smoke).
3. Null never shown as 0 — **pass** (formatter-level test + confidence smoke).
4. 422 / 404 / 500 are distinct states, never "No data" — **pass** (test).
5. Rejected transform disables Analyze — **pass** (`analyze_allowed` test; UI gates button).
6. Snapshot surfaces hash / columns / row_count and offers CSV download — **pass**
   (render test; download_button decodes `csv_base64`).
7. Frontend never imports `nestor_delta` / never recomputes — **pass** (isolation test).
8. Live FastAPI + Streamlit e2e — **pass**. Bundled Spain completed audit and
   baseline-only analysis. The verified Eurostat preset completed snapshot,
   frozen-snapshot audit, and baseline-only analysis against the live services.
   The snapshot contained 228 monthly rows for 2005-01..2023-12 with SHA-256
   `7f16537206cbb37b1b3b9ee33b9b233eb6b50865d59a03169d3651a30a3664ca`.
9. Desktop/mobile width check — **pass**. The live page was inspected at desktop
   and narrow widths; controls stayed within their containers and the main view
   had no horizontal overflow. The in-app browser's forced-viewport screenshot
   compositor duplicated fragments, but DOM geometry and the restored native
   narrow viewport were correct.

## Live run used for acceptance
```bash
uvicorn nestor_delta_service.app:app --app-dir src --host 0.0.0.0 --port 8000
export DELTA_API_BASE_URL=http://127.0.0.1:8000
PYTHONPATH=src streamlit run src/nestor_delta_web/streamlit_app.py --server.port 8501
```

## Backend contract gaps found
- None blocking. `/snapshot`, `/audit`, `/analyze` returned exactly the contract
  shapes. Note: `unit` / `seasonal_adjustment` come back `"unknown"` for bundled
  cases (metadata not in case config) — the UI shows `unknown` honestly rather
  than guessing, which is correct behavior, but populating case metadata later
  would improve the audit page.
