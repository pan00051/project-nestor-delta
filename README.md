# Nestor Delta

Nestor Delta is a deterministic relationship-reliability engine for monthly
multivariate time series. It measures lagged relationships on explicitly
transformed data, tracks whether those relationships remain stable, and admits
only adequately supported evidence before prediction.

It reports co-movement and predictive usefulness, not causation. An honest
`baseline_only` result is a valid outcome.

## What Is Included

The completed pipeline covers:

1. deterministic baselines and lagged relationship scoring;
2. trust gating, dynamic weights, and resource-adaptive filtering;
3. strict real-data case validation and rolling-origin evaluation;
4. S7 transformed relation scoring (`none`, `diff`, or `log_diff`);
5. S8 uncertainty intervals and sample-aware noise floors;
6. S9 stability, uncertainty, and relationship lifecycle states;
7. S10 evidence selection and prediction confidence;
8. a thin FastAPI adapter and Streamlit interface for bundled cases, CSV
   uploads, and exact Eurostat series definitions.

The S7-S10 pipeline is deliberately conservative: stability is computed from
the transformed S7 trajectory, never from legacy level Pearson correlations.
Insufficient evidence remains `null`; the frontend does not turn it into zero
or invent a conclusion.

## Quick Start

Tests require Python 3.9 or newer. Run the complete suite with pytest
(`pip install -e '.[dev]'`):

```bash
python3 -m pytest -q          # 171 tests
```

`python3 -m unittest discover -s tests` runs only the 145 unittest-style tests.
It **cannot** collect the 26 ground-truth tests, which are plain functions - and
those are the only tests that check whether the detector actually detects. Use
it as a stdlib-only smoke check, never as the acceptance run.

Run the website with two processes:

```bash
python -m pip install -r requirements-web.txt
uvicorn nestor_delta_service.app:app --app-dir src --host 0.0.0.0 --port 8000
```

In a second shell:

```bash
export DELTA_API_BASE_URL=http://localhost:8000
PYTHONPATH=src streamlit run src/nestor_delta_web/streamlit_app.py --server.port 8501
```

Open [http://localhost:8501](http://localhost:8501). The API health endpoint is
at [http://localhost:8000/health](http://localhost:8000/health).

The full website guide is in
[`docs/WEBSITE_FRONTEND_RUN.md`](docs/WEBSITE_FRONTEND_RUN.md).

## How It Works

```text
monthly input
  -> data audit and explicit transform declarations
  -> S7 transformed relation scoring
  -> S8 rolling evaluation and noise floor
  -> S9 stability, uncertainty, and lifecycle
  -> S10 Evidence Gate
  -> baseline-only or evidence-supported prediction report
```

The analysis package is the source of truth. The service adapter only validates,
composes, and serializes existing outputs into `delta.report.v1`; the Streamlit
app calls that API over HTTP and never imports or recomputes the algorithm.

### Relationship object

Each relationship keeps the existing source, target, lag, and signed weight,
then adds only:

- `stability`
- `uncertainty`
- `selected`

Direction is represented by `sign(weight)`. Lifecycle is reported separately as
`birth -> strengthening -> stable -> decaying -> dead`.

### Website API

| Endpoint | Purpose |
|---|---|
| `GET /health` | service health |
| `GET /schema/report` | Report JSON contract metadata |
| `POST /snapshot` | fetch and freeze an exact Eurostat definition |
| `POST /audit` | validate monthly data and transform declarations |
| `POST /analyze` | run the existing S1-S10 pipeline synchronously |

Validation errors, analysis failures, missing resources, and valid empty results
remain distinct. There is currently no report database, account system, generic
Eurostat catalog search, or public deployment configuration.

## Evidence And Results

The repository keeps frozen fixtures and committed reports so claims can be
checked without trusting a live service.

- **S7:** independent random walks no longer receive high transformed relation
  scores, while the known lagged synthetic relationship is retained.
- **S8:** rolling-origin intervals showed that the earlier Spain `+7.11%`
  validation improvement was not distinguishable from noise, while the pandemic
  degradation was.
- **S9:** Fixture C detects a known relationship death in all 100 runs within the
  required horizon; noise fixtures are not promoted to `stable` or
  `strengthening`.
- **S10:** Fixture D raises selection precision from a permissive fixed threshold
  to evidence-gated selection while preserving the no-evidence baseline fallback.
- **Spain retail:** the frozen 216-month Eurostat case does not establish a win
  over persistence. The current website correctly returns a successful
  `baseline_only` report rather than presenting false confidence.

Start with these artifacts:

- [`reports/s7_relation_measurement_summary.md`](reports/s7_relation_measurement_summary.md)
- [`reports/evaluation_power/dual_window_recheck.md`](reports/evaluation_power/dual_window_recheck.md)
- [`reports/s9_relation_lifecycle_summary.md`](reports/s9_relation_lifecycle_summary.md)
- [`reports/s10_evidence_confidence_summary.md`](reports/s10_evidence_confidence_summary.md)
- [`reports/spain_retail_eurostat_2008_2025/real_budget_sweep_summary.md`](reports/spain_retail_eurostat_2008_2025/real_budget_sweep_summary.md)

## Repository Guide

```text
src/nestor_delta/          analysis pipeline (source of truth)
src/nestor_delta_service/  thin FastAPI adapter and Eurostat intake
src/nestor_delta_web/      Streamlit UI and pure rendering helpers
tests/                     algorithm, contract, and frontend tests
scripts/                   deterministic report and case entry points
cases/                     frozen real-data inputs and provenance
data/                      synthetic and regression fixtures
reports/                   committed numerical evidence
docs/                      contracts, run guides, and capability notes
```

Project-level documents have distinct roles:

- [`BLUEPRINT.md`](BLUEPRINT.md): stable scope and architecture rules.
- [`HANDOFF.md`](HANDOFF.md): current state and next decision only.
- [`RUNBOOK.md`](RUNBOOK.md): collaboration workflow.
- [`REPRODUCIBILITY.md`](REPRODUCIBILITY.md): verification commands.
- [`docs/README.md`](docs/README.md): documentation index.
- [`S7-S10的规则.md`](S7-S10的规则.md): frozen S7-S10 scope and acceptance rules.

## Boundaries

- Core conclusions are deterministic and past-only.
- Transform declarations are explicit; the engine does not silently guess.
- Prediction error cannot feed back into S10 relationship selection.
- `null` means insufficient evidence or not evaluated, never zero.
- Eurostat intake freezes exact data definitions and hashes the resulting CSV.
- The project combines established statistical methods and does not claim a new
  causal or forecasting algorithm.
