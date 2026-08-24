# M3 Architecture Principles

Date: 2026-08-24

Status: governs future implementation. Only the additive Report
`configuration` block and the independent selected-relation ledger are started
now.

## Strict And Approximate Values

Approximate values may consume strict results. Strict values must never consume
approximate results. The dependency direction is the rule; execution order is
secondary.

Test for approximation: is this value a substitute for something we could have
measured correctly? If yes, it may be diagnostic but must not decide selection.
If it measures a different quantity, such as `stability` measuring temporal
consistency rather than relation strength, it may participate in decisions but
needs its own ground truth.

Candidate choice is upstream of this rule. It is governed by preregistration and
comparison counting, not by reordering computations.

## Principled Adaptation

An adaptive parameter is safe when its rule can be written before seeing any
data: sample-size-aware noise floors and FDR thresholds are examples.
Adaptation justified only by "it works better empirically" is learned
adaptation; it needs a generator, hard constraints, and versioning before it can
ship.

Open gaps:

- Rolling lifecycle windows should scale with `n`; the current 36-month cap is
  published in `configuration` but is not the final rule.
- `lag_window` needs a principled upper bound relative to sample size. The true
  lag remains domain knowledge, not a value learned from the same data.

## Data-Dependent Branches

```
effective_configuration = g(snapshot, analysis_params, pipeline_version)
report                  = f(snapshot, analysis_params, pipeline_version)
```

The effective configuration is a published *result* of the first three terms,
not a fourth independent input, so `report = f(snapshot, analysis_params,
pipeline_version)` remains valid when the algorithm branches on data, provided
every branch input is inside the snapshot or explicit params. Any override a
user can set is an analysis param and belongs in the second term. The report
must not depend on wall clock, caller identity, other users' data, machine state,
remote config, or execution history.

Any value that can change a conclusion must be visible in the Report. M3 starts
this with an additive `configuration` block that publishes effective gate terms,
rolling-window rules, diagnostic noise-floor role, transform declarations, and
sample/count inputs.

Every data-dependent branch needs its own ground-truth fixtures, including
boundaries. Continuous adaptation is preferred over discrete branches; when a
discrete rule is unavoidable, the rule must be displayed to users.

## No Cross-User Threshold Learning

Default reports must not learn thresholds from other users' data. That would
make reproducibility and audit chains depend on hidden datasets and create
consent/compliance obligations. If cross-user learning ever exists, it must be a
separate explicit mode, never mixed into the default report.

## Selected-Relation Ledger

Selected relations need a real-time record of whether they later continue
out-of-sample. This is measurement, not optimization, and must stay outside the
Report body. M3 starts an append-only JSONL ledger at the API Run boundary for
completed runs with selected relations.

Each ledger row records: `mode`, `run_id`, `snapshot_hash`, `target`, `source`,
`lag`, `sign`, `score`, `stability`, `generated_as_of`, and `pipeline_version`.
The default path is `/tmp/nestor_delta_relationship_ledger.jsonl`; set
`NESTOR_RELATIONSHIP_LEDGER_PATH` to place it on durable storage.

Ledger writes are fail-soft. A filesystem, permission, or capacity failure must
be logged and must never turn a successful analysis into a failed request.
Capabilities publish the resolved ledger path and whether it is configured as
durable. Public deployments that claim to accumulate a record must mount a
persistent volume and set `NESTOR_RELATIONSHIP_LEDGER_PATH` to that mount.

Backtests may use the same shape but must be marked `mode: "backtest"`.

## Calibration Versus Fishing

Calibration can run many times when the criterion is an operating
characteristic with independently known truth: sensitivity, false-positive
rate, lag recovery. Fishing starts when the criterion is whether a real case
passes.

Rules:

- Tune thresholds only on ground-truth fixtures.
- Split burnable calibration cases from sealed demo cases before looking.
- Record every run against real data in an attempt log.
