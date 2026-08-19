# Nestor Delta Website — Run (W5)

Two processes: the FastAPI backend (adapter over S1–S10) and the Streamlit
frontend. The frontend talks to the backend over HTTP only.

The UI presents one three-step flow: choose data, audit and declare transforms,
then read or download the Report JSON v1 result.

## Environment
- `DELTA_API_BASE_URL` — backend base URL the Streamlit server calls.
  Default `http://localhost:8000`. No production URL is hard-coded.

## Install
```bash
python -m pip install -r requirements-web.txt
```

## Run
```bash
# 1) backend
uvicorn nestor_delta_service.app:app --app-dir src --host 0.0.0.0 --port 8000

# 2) frontend (new shell)
export DELTA_API_BASE_URL=http://localhost:8000
PYTHONPATH=src streamlit run src/nestor_delta_web/streamlit_app.py
```

## Data sources
- **Bundled case** — pick a Spain case → Audit → declare transforms → Analyze.
- **Upload CSV** — an already-aligned monthly CSV + target/signals/train_end/lag_window.
- **Eurostat** — a verified preset (`ei_bssi_m_r2`) or the manual series editor;
  Fetch snapshot (rows/coverage/source/SHA-256, download CSV) → Audit → Analyze.
  There is no catalog/search; nothing is a fabricated search result.

## Tests (no backend needed)
```bash
python -m unittest tests.test_website_frontend
```
