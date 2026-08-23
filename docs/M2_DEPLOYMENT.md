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
streamlit run src/nestor_delta_web/streamlit_app.py --server.address 0.0.0.0 --server.port $PORT --server.headless true
```

Runtime: Python `3.10.14`, locked in both `runtime.txt` and the Docker base image.

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
