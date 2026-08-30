# G0 Draft Quarantine — 2026-08-30

This directory preserves four quarantined G0 draft files as defect evidence.
They are not accepted, must not be cited as shipped capability, and must not be
used as dependencies for tests, documentation claims, fixtures, or product
decisions.

## Quarantined Files

| Original path | Quarantined path | Original filesystem timestamp |
|---|---|---|
| `docs/ALGORITHM_EXPERIMENTS.md` (historical) | `docs/evidence/G0_DRAFT_QUARANTINE_2026-08-30/ALGORITHM_EXPERIMENTS.md` | `2026-08-29 18:04:11` |
| `docs/algorithm_seed_sets_v1.json` (historical) | `docs/evidence/G0_DRAFT_QUARANTINE_2026-08-30/algorithm_seed_sets_v1.json` | `2026-08-29 18:04:11` |
| `scripts/run_algorithm_experiment.py` (historical) | `docs/evidence/G0_DRAFT_QUARANTINE_2026-08-30/run_algorithm_experiment.py` | `2026-08-29 18:04:11` |
| `tests/test_algorithm_experiment_log.py` (historical) | `docs/evidence/G0_DRAFT_QUARANTINE_2026-08-30/test_algorithm_experiment_log.py` | `2026-08-29 18:04:11` |

The shared timestamp indicates a batch write from an unrecorded session. These
files were local, untracked, and unreviewed before T5; they are preserved here
only so the D2 finding remains auditable.

## Handling Rules

`algorithm_seed_sets_v1.json` is invalidated as a holdout seed set. A holdout
set is only valuable if its creation time, method, and pre-experiment status are
traceable. G0 must regenerate the seed set when formally started, and the first
experiment-log entry must record the generation parameters, timestamp,
`pipeline_version`, and a statement that no experiment had been run against the
new holdout before generation was recorded.

`run_algorithm_experiment.py` and `test_algorithm_experiment_log.py` may be read
as reference implementations. They must not be accepted directly as G0
deliverables.
