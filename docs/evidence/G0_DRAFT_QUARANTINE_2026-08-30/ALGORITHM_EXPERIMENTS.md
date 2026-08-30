# Algorithm Exploration Measurements

This is development infrastructure, not portfolio evidence. It exists so dense
algorithm exploration leaves a mechanical trail instead of scattered one-off
reports.

## Current Rule

During the algorithm exploration phase, every serious parameter or algorithm
candidate should record at least:

- detection floor from the S-GT-4 sweep
- false-positive rate across the configured negative seeds
- `pipeline_version`
- `source_revision`
- `criteria_version`
- a mechanical `PASS` / `FAIL` / `INCONCLUSIVE` verdict with rule ids

Run the tuning measurement:

```bash
python scripts/run_algorithm_experiment.py
```

It appends one JSON object to `reports/algorithm_experiments.jsonl` and prints
the same row. `reports/` is ignored, so copy important rows into a review note
or evidence document only when a result graduates from exploration.

## Seed Separation

Seed sets live in `docs/algorithm_seed_sets_v1.json`.

- `tuning` is for day-to-day exploration.
- `holdout` is for stage-level checks only.

Do not run holdout after every failed tuning idea. A holdout result remains a
holdout only while it is not used to steer the next tweak.

```bash
python scripts/run_algorithm_experiment.py --seed-set holdout
```

## Frozen Controls

This runner does not change Evidence Gate terms and does not use prediction or
validation error to select relations. The frozen gate terms still live in
`src/nestor_delta/evidence_gate.py` and
`src/nestor_delta_service/adapter.py`, and any change to them remains a separate
boundary decision.
