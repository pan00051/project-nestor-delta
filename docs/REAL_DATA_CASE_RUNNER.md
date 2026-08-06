# Sprint 6 Real Data Case Runner

Sprint 6 is a narrow bridge from controlled benchmarks to author-prepared real data.

It is not a public upload product, dashboard, API connector, or automatic data-cleaning system. It only accepts a local CSV that has already been aligned and cleaned by the author, plus a JSON config that declares the target, candidate signals, and time split.

## Command

```bash
python scripts/run_real_case.py cases/<case_name>/case.json
```

## Input Contract

The CSV must be one row per time point, sorted or sortable by an ISO-like date column:

```text
date,target,signal_1,signal_2,signal_3
2020-01,123.4,10.0,4.2,0.1
2020-02,125.1,10.3,4.1,0.2
```

All target and candidate signal columns must be numeric. Missing values, frequency alignment, source API issues, and business-specific cleaning happen before this runner. The first S6 protocol only accepts contiguous monthly data in `YYYY-MM` format.

Example config:

```json
{
  "case_name": "tomato_gold",
  "csv": "data.csv",
  "date_column": "date",
  "target": "gold_price",
  "candidate_signals": ["tomato_price", "oil_price", "cpi", "usd_index"],
  "frequency": "monthly",
  "lag_window": 3,
  "train_end": "2020-12",
  "test_start": "2021-01",
  "max_selected_signals": 3,
  "seasonal_period": 12,
  "output_dir": "reports",
  "notes": "Exploratory real-data case; co-movement only."
}
```

## Outputs

The runner writes CSV files designed for later manual charting:

- `relation_ranking.csv`
- `prediction_metrics.csv`
- `predictions_vs_actual.csv`
- `resource_tradeoff.csv`
- `summary.md`

## Guardrails

- The author may define the candidate pool, but must not manually rank it.
- The config must include every required field and no unknown fields.
- CSV dates must already be contiguous monthly values; the runner does not sort, fill, interpolate, or clean.
- Ranking and selected signals are computed from train rows only.
- Test rows are used only for out-of-sample evaluation.
- CSV column order is not signal priority; candidates are normalized to deterministic ordering before scoring.
- Ranking order is deterministic: relation score descending, then signal name, then lag.
- If selected real-data signals are collinear, the runner removes lower-ranked overlapping signals first and keeps the full ranking in the report.
- If no selected signal satisfies numerical stability requirements, the runner keeps baseline outputs only.
- The report describes co-movement and out-of-sample predictive usefulness only.
