# M2 Thin-Slice Deployment

Deployment target: Render Blueprint (`render.yaml`).

Topology: two web services, cross-origin.

FastAPI service:

```sh
uvicorn nestor_delta_service.app:app --host 0.0.0.0 --port $PORT --workers 1
```

Streamlit service:

```sh
streamlit run src/nestor_delta_web/streamlit_app.py --server.address 0.0.0.0 --server.port $PORT --server.headless true
```

Runtime: Python `3.10.14`, locked in both `runtime.txt` and `render.yaml`.

Dependencies: deployment installs `requirements-web.txt`. `requirements-lock.txt`
documents that core analysis has no third-party runtime dependency; web serving
uses the separated web requirements file.

Bundled case packaging: M2 deploys from a source checkout with `PYTHONPATH=src`;
the package is not pip-installed as a wheel. This preserves
`adapter.py` repository-root lookup for `cases/`. If a future deployment installs
the package into `site-packages`, `cases/` must move to package data first.

Single-worker constraint: FastAPI is explicitly started with `--workers 1`
because `RunStore` is process-local. Multi-worker deployment is prohibited until
run storage is backed by shared storage.

Deployment exclusions: `.dockerignore` excludes `private/`, `.venv/`,
`__pycache__/`, `data/synthetic*`, and `reports/` from container-style deploy
artifacts.
