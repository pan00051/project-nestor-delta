# M2 Thin-Slice Deployment

Deployment target: Railway project `nestor-delta-m2`.

Topology: two web services, cross-origin.

The repository configuration is `railway.json`; both Railway services build the
same Python 3.10.14 image from `Dockerfile`. `scripts/start-railway-service.sh`
selects the checked-in command from Railway's built-in `RAILWAY_SERVICE_NAME`:

FastAPI service `api`:

```sh
uvicorn nestor_delta_service.app:app --host 0.0.0.0 --port $PORT --workers 1
```

Streamlit service `web`:

```sh
streamlit run src/nestor_delta_web/streamlit_app.py --server.address 0.0.0.0 --server.port $PORT --server.headless true --browser.gatherUsageStats false
```

Runtime: Python `3.10.14`, locked by the Docker base image. Railway does not use
`runtime.txt` for this Dockerfile build, so there is only one version source.

Dependencies: deployment installs `requirements-web.txt`. `requirements-lock.txt`
documents that core analysis has no third-party runtime dependency; web serving
uses the separated web requirements file.

The only project-defined runtime environment variable is `DELTA_API_BASE_URL`,
set on `web` to the generated public URL of `api`. `PORT` and
`RAILWAY_SERVICE_NAME` are Railway-provided variables.

Bundled case packaging: M2 deploys from copied source with `PYTHONPATH=/app/src`;
the package is not pip-installed as a wheel. This preserves
`adapter.py` repository-root lookup for `cases/`. If a future deployment installs
the package into `site-packages`, `cases/` must move to package data first.

Single-worker constraint: FastAPI is explicitly started with `--workers 1`
because `RunStore` is process-local. Multi-worker deployment is prohibited until
run storage is backed by shared storage.

Demo runtime policy: Railway Serverless is disabled for both services. A cold
start in front of an audience costs more than the small amount of idle hosting
saved during the M2/M5 demonstration window. Keep both services warm through the
demo. After the demo, Serverless may be restored only if cold-start latency and
process-lifetime run retention are acceptable; otherwise leave it disabled until
run storage is shared and durable.

Run retention: `max_runs: 100` is a process-local capacity bound, not a durability
guarantee. A deploy, restart, crash, or Serverless sleep destroys `RunStore` and
makes all prior run IDs return 404. With Serverless enabled, retention can be as
short as the next idle sleep. The demo therefore keeps API Serverless disabled.

Deployment exclusions: `.railwayignore` excludes local files before `railway up`
creates its upload archive. `.dockerignore` applies the same exclusions to the
Docker build context. Both exclude `private/`, `.venv/`, `__pycache__/`,
`data/synthetic*`, and `reports/`.

Frozen Eurostat evidence: the preset fixture is committed at
`fixtures/eurostat/ei_bssi_m_r2_es_industry_construction_2005_2023.json`. It
records the capture time, raw JSON-stat payloads for both series, and snapshot
SHA-256 `7f16537206cbb37b1b3b9ee33b9b233eb6b50865d59a03169d3651a30a3664ca`.
`tests/test_eurostat_intake.py` rebuilds the snapshot from those payloads and
requires that exact hash. The preset path injects this fixture; live Eurostat
access is not on the demonstration path.

## M2 public verification record

Public services:

- FastAPI: `https://api-production-9849.up.railway.app`
- Streamlit: `https://web-production-31a89.up.railway.app`

Four deployment unknowns:

1. Cloud egress: yes. A live, snapshot-free request from the deployed API reached
   Eurostat and returned 200 with 228 rows. Its generated snapshot SHA-256 was
   `7f16537206cbb37b1b3b9ee33b9b233eb6b50865d59a03169d3651a30a3664ca`,
   matching the committed fixture. The demo path still uses the fixture.
2. Bundled-case reachability: yes. The deployed Docker image ran
   `spain_retail_eurostat_2008_2025` from `cases/` and returned 200,
   `baseline_only`, 216 observations, and snapshot SHA-256
   `a8c01df041db4d835baf83a459ae65194a4d5c9bca157753d56cd6259d106445`.
   This proves `REPO_ROOT=/app` under `COPY . ./` and `PYTHONPATH=/app/src`.
3. Cold/restart timing: the API produced a confirmed Serverless stop event at
   `2026-08-23T15:36:19Z`; its first public health request returned 200 with
   2.378 seconds TTFB and 2.379 seconds total. The Web service does not sleep in
   demo configuration. A controlled restart showed Uvicorn ready at
   `16:48:37.484Z` and Streamlit ready at `16:48:37.889Z` (0.404 seconds inside
   the process). A human stopwatch pass in an unauthenticated browser measured
   `Starting Container` to interactive first screen at under 2 seconds. The
   discarded 69.902-second browser-tool result is not a cold-start measurement
   and must not be used.
4. Topology: two services on separate Railway origins. Streamlit calls FastAPI
   from the Streamlit server through `requests`, so CORS has no real consumer in
   M2. Production OPTIONS and Origin-bearing GET probes returned 200 with
   `Access-Control-Allow-Origin: *`; this is a synthetic boundary check for the
   next-cycle standalone frontend, not proof of a production browser consumer.
   Both versioned routes and legacy aliases pass through the single
   `allow_request` auth dependency. With credentials disabled, no cookie-based
   cross-origin auth behavior is claimed.

Online validation:

- `/api/v1/capabilities` returned pipeline `s10.sha256.7763cf123030` and the
  structured Eurostat preset ID/label/dataset contract.
- `NESTOR_API_BASE=https://api-production-9849.up.railway.app pytest
  tests/ground_truth -v` passed all 21 tests in 73.59 seconds.
- The online positive control returned effect score `0.5844220533473201`; the
  negative control returned HTTP 200 with outcome `baseline_only`.
- An unauthenticated browser completed audit and analysis for bundled case
  `spain_retail_eurostat_2008_2025`, producing `Baseline retained` without any
  Nestor account or application login.

## Known test-tool issue

Chrome and the in-app Browser control layer can time out while closing,
navigating away from, or taking a DOM snapshot of a Streamlit tab. One locator
wait also timed out after the product process was already ready. This is an
automation/control-interface issue and is excluded from M2 product acceptance.
Do not use the discarded 69.902-second value as product latency. A minimal
Streamlit-on-Railway comparison is optional follow-up work, not an M2 blocker.
