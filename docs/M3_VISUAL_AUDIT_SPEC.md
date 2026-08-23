# M3 Visual Audit And State Specification

Date: 2026-08-24

M3 changes the frontend task from "draw four states from mocks" to "audit what
the existing Streamlit UI already claims, fix contradictions, then specify the
states." The rule for every displayed field is: if we cannot say what would make
the field change, it must not carry selection or threshold weight.

## Decorative Field Audit

| Field rendered | Data source | What makes it change? | Participates in a decision? | May UI present it as threshold/pass state? |
| --- | --- | --- | --- | --- |
| `schema_version` | Report JSON root | Contract version emitted by adapter/schema | Yes, frontend rejects malformed/mismatched reports | Yes, as compatibility only |
| `outcome` | Report JSON root | API result class: ok, baseline_only, ok_to_analyze, snapshot_ready, validation_error, not_found, analysis_failure | Yes, selects screen state | Yes, as state, not evidence quality |
| `generated_as_of` | Report JSON root | Adapter report generation/as-of timestamp | No | No |
| `case.name` | Report JSON `case` | User-selected bundled case or upload metadata | No | No |
| `case.target` | Report JSON `case` | Request target field | Yes, scopes relations and report context | No |
| `case.candidate_signals` | Report JSON `case` | Request candidate list | Yes, defines candidate pool | No |
| `case.frequency` | Report JSON `case` | Input/report frequency | Intake compatibility only | No |
| `case.n_observations` | Report JSON `case` | Number of accepted rows | Yes, indirectly affects sample support and p-values | No, except support context |
| `case.train_end` | Report JSON `case` | Request train cutoff | Yes, controls training window | No |
| `case.lag_window` | Report JSON `case` | Request lag search window | Yes, controls relation scan and comparisons | No |
| `snapshot.hash` | Report JSON `snapshot` | Exact snapshot bytes | Provenance/determinism only | No |
| `snapshot.source` | Report JSON `snapshot` | Data source mode | No | No |
| `snapshot.provenance.series.updated` | Snapshot provenance | Upstream source metadata changes | Provenance only | No |
| `row_count` | Snapshot response | Snapshot CSV row count | Intake context only | No |
| `columns` | Snapshot response | Snapshot CSV columns | Builds frozen upload payload | No |
| `csv_base64` | Snapshot response | Snapshot bytes | Yes, binds later analysis input | No |
| `data_audit.date_axis.continuous` | Audit/report `data_audit` | Missing or duplicate months | Yes, intake validity | Yes, intake pass/block |
| `data_audit.date_axis.expected_months` | Audit/report `data_audit` | Date span | Intake context | No |
| `data_audit.date_axis.present` | Audit/report `data_audit` | Accepted month count | Intake context | No |
| `data_audit.date_axis.missing_months` | Audit/report `data_audit` | Missing date labels | Yes, validation/error context | Yes, intake issue |
| `data_audit.date_axis.duplicate_months` | Audit/report `data_audit` | Duplicate date labels | Yes, validation/error context | Yes, intake issue |
| Signal `sample_count` | Audit `data_audit.signals[]` | Non-null numeric samples per signal | Yes, later support/p-values | No, except support context |
| Signal `unit` | Audit `data_audit.signals[]` | Source metadata/input columns | No | No |
| Signal `seasonal_adjustment` | Audit `data_audit.signals[]` | Source metadata/input columns | No | No |
| Signal `coverage.start/end` | Audit `data_audit.signals[]` | First/last valid sample | Intake context | No |
| Signal `lag1_acf` | Audit `data_audit.signals[]`, `transform_diagnostics[]` | Persistence of raw level series | Yes, flags transform risk | Yes, as transform-risk flag only |
| Signal `highly_persistent_risk` | Audit diagnostics | `lag1_acf > 0.95` | Yes, can block raw-level declaration | Yes, intake/transform risk |
| Transform `declared` | User choice/API diagnostics | User declaration | Yes, controls scoring transform and validation | Yes, accepted/rejected declaration |
| Transform `verdict` | API diagnostics | Declared transform vs persistence risk | Yes, blocks analysis when rejected | Yes, accepted/rejected |
| `baseline.name` | Report `baseline` | Baseline strategy | Decision context only | No |
| `baseline.mae` | Report `baseline` | Baseline forecast error on label window | Context/evaluation only | No |
| `evaluation.rolling_origin.median` | Report `evaluation` | Rolling-origin skill estimate | Report evidence context, not relation gate | No |
| `evaluation.rolling_origin.low/high` | Report `evaluation` | Rolling-origin interval | Report evidence context | No |
| `evaluation.rolling_origin.folds` | Report `evaluation` | Number of rolling-origin folds | Evidence context | No |
| `evaluation.rolling_origin.resolves` | Report `evaluation` | Whether interval excludes zero | Evidence context | Yes, evaluation resolution only |
| Report `noise_floor.threshold` | Report root `noise_floor` | Sample count, comparisons, alpha | No in v1 Evidence Gate | No. Diagnostic comparison scale only |
| Report `noise_floor.sample_count` | Report root `noise_floor` | Largest relation sample count | No | No |
| Report `noise_floor.comparisons` | Report root `noise_floor` | Lag window and candidate count | No | No |
| Report `noise_floor.alpha` | Report root `noise_floor` | Configured alpha | No | No |
| Relation `source` | `relations[]` | Candidate signal name | Yes, identifies relation | No |
| Relation `target` | `relations[]` | Target signal name | Yes, identifies relation | No |
| Relation `lag` | `relations[]` | Lag with max absolute transformed correlation | Yes, relation definition | No |
| Relation `transform` | `relations[]` | Declared scoring transform | Yes, relation definition | No |
| `effect.score` | `relations[].effect.score` | Full train-window absolute transformed correlation | Yes, through FDR p-value, not by noise_floor | Yes, only with FDR/result context |
| `effect.weight` | `relations[].effect.weight` | Signed transformed correlation at selected lag | Ranking/context | No |
| `effect.sign` | `relations[].effect.sign` | Sign of `effect.weight` | Direction context | No |
| `effect.noise_floor` | `relations[].effect.noise_floor` | Sample count, comparisons, alpha | No in v1 Evidence Gate | No. Must not read as pass/fail |
| `effect.effect_size_vs_noise_floor` | Relation effect | Ratio of score to diagnostic floor | No in v1 Evidence Gate | No. Diagnostic only |
| `significance.p_value` | Relation significance | Correlation score and sample count | Yes, FDR gate | Yes, FDR only; tiny values display as `< 1e-12` |
| `significance.fdr_threshold` | Relation significance | Benjamini-Hochberg cutoff over candidate p-values | Yes, FDR gate | Yes |
| `significance.clears` | Relation significance | `p_value <= fdr_threshold` | Yes, FDR gate | Yes |
| `stability` | Relation root | Recent rolling strength/sign/lag consistency | Yes, min stability gate | Yes |
| `uncertainty` | Relation root | Std dev of recent rolling weights | Yes, max uncertainty gate | Yes |
| `sample_support` | Relation root | Relation sample count vs reference sample count | Yes, min support gate | Yes |
| `lifecycle.state` | Relation lifecycle | End-of-sample trajectory shape | Visual state, not Evidence Gate selector by itself | Yes, as lifecycle state, not alarm |
| `lifecycle.points` | Relation lifecycle | Count of rolling trajectory points | Evidence sufficiency context | No |
| `selected` | Relation root | Evidence Gate result | Yes, final relation inclusion | Yes |
| `reason_code` | Relation root | First failed gate or selected | Yes, explains selection/rejection | Yes |
| `reason_text` | Relation root | Backend/user-facing reason for `reason_code` | Explanation only | No extra threshold |
| `trajectory[].date` | Relation trajectory | Window end date/as-of date | Timeline x-axis | No |
| `trajectory[].score` | Relation trajectory | Rolling transformed relation score | Lifecycle evidence | No single-point gate |
| `trajectory[].sign` | Relation trajectory | Rolling weight sign | Lifecycle evidence | No |
| `trajectory[].lag` | Relation trajectory | Rolling selected lag | Lifecycle evidence | No |
| `selection.fit_status` | Report selection | Whether selected relations exist | Yes, selects baseline/delta final mode | Yes, report state |
| `selection.final_mode` | Report selection | `delta` vs `not_evaluated` | Yes, report state | Yes, report state |
| `selection.selected_count` | Report selection | Count of selected relations | Yes, summary | Yes, count only |
| `selection.selected_sources` | Report selection | Selected relation sources | Yes, model input set | No |
| `prediction_confidence.confidence` | Report confidence | Confidence component combination, nullable | Report confidence only | Yes when non-null; null is insufficient |
| `prediction_confidence.components.*` | Report confidence | Stability, uncertainty, support, residual inputs | Confidence explanation | No standalone pass/fail |
| `prediction_confidence.capped_by` | Report confidence | Component that capped confidence | Confidence explanation | No |
| `narrative.headline` | Report narrative | Adapter outcome and selected count | No independent decision | No |
| `narrative.lines[]` | Report narrative | Adapter outcome and reasons | No independent decision | No |
| `warnings[]` | Report warnings | Adapter warnings | Advisory only | No |
| `error.code` | Error response | Validation/not-found/analysis failure class | Yes, error state | Yes, error class |
| `error.message` | Error response | Backend error detail | Explanation | No |
| `error.field` | Error response | Invalid or missing input field | Yes, directs repair | Yes, input repair target |
| `error.detail` | Error response | Backend structured detail | Debug/explanation | No |

## Fixed Online Contradictions

1. Homepage lede now lists the real selection logic: FDR, stability,
   uncertainty, and sample support. It no longer says relationships survive the
   noise floor.
2. The relation score tile no longer displays `floor ...` under the score.
   Noise floor moved into a diagnostic caption:
   `Diagnostic comparison scale: noise floor ...; effect/noise .... This scale
   is not part of the evidence gate.`

## Four-State Screen Specification

Public baseline-only screenshot: [m3_baseline_only_public.jpg](m3_baseline_only_public.jpg).

| State | Trigger | Field | Encoding semantics | Streamlit implementation | Degradation |
| --- | --- | --- | --- | --- | --- |
| `ok` | `outcome=ok`, selected >= 1 | Decision header | Delta selected defendable relations | `delta-decision selected`, headline from narrative | If narrative missing, default selected headline |
| `ok` | selected >= 1 | Evidence table | Sorted relation evidence is primary report object | Relationship expanders plus Analyst table | Until true frontend, table remains the main map |
| `ok` | selected relation | `effect.score` | Strength of full-window transformed relation | Metric tile `Score` | Null -> dash and insufficient context, never 0 |
| `ok` | selected relation | FDR fields | Statistical evidence gate | Caption `p=... · FDR threshold=... · clears FDR=...` | Tiny p values display `< 1e-12` |
| `ok` | selected relation | `stability` | Minimum rolling consistency gate | Metric tile | Null -> `insufficient` |
| `ok` | selected relation | `uncertainty` | Maximum rolling uncertainty gate | Metric tile | Null -> `insufficient` |
| `ok` | selected relation | `sample_support` | Minimum sample support gate | Metric tile | Null -> `insufficient` |
| `ok` | selected relation | `noise_floor` | Diagnostic comparison scale, not selection | Diagnostic caption and Analyst table column | Never displayed as floor/pass/fail under Score |
| `ok` | selected relation | `lifecycle.state` | Relation life-cycle color/state | Five-step track and badge tone | Unknown enum is preserved as neutral text |
| `ok` | selected relation | `trajectory[].date/score` | Time-indexed relation strength | `st.line_chart(frame, x="date", y="score")` | Missing/empty -> explicit no timeline caption |
| `baseline_only` | `outcome=baseline_only`, selected = 0 | Decision header | Successful legal-empty result; baseline retained | `delta-decision baseline` | Never "No data" |
| `baseline_only` | selected = 0 | Rejection reasons | Why every candidate was refused | Relationship expanders and Analyst table, sorted by backend order | Missing reason -> raw code text |
| `baseline_only` | selected = 0 | Baseline MAE | Baseline quality context | Metric tile | Null -> dash |
| `baseline_only` | selected = 0 | Confidence | Evidence insufficient for prediction confidence | Metric `—` with `insufficient` note | Null is never 0% |
| `baseline_only` | each rejected relation | `reason_code/reason_text` | First failed evidence gate | Tone text in relation expander | Raw unknown code preserved |
| `baseline_only` | each rejected relation | `noise_floor` | Diagnostic only | Caption/table only | Must not imply it rejected the relation |
| `422 validation_error` | `outcome=validation_error` or HTTP 422 | Error class | Input rejected, not empty result | `st.error("Input rejected · code")` | Never rendered through report empty state |
| `422 validation_error` | invalid input | `error.field` | Field to repair | `Field: ...` caption | If null, show message/detail |
| `422 validation_error` | invalid input | `error.message/detail` | What to fix and technical detail | Message plus expander | No relation/evidence UI shown |
| nullable field null | any state | Numeric fields | Evidence insufficient/not evaluated | Formatter returns `—`; metric note says `insufficient` where applicable | Never 0, never blank |
| nullable field null | relation | `trajectory=null` or `[]` | Timeline evidence absent | Explicit caption: no timeline chart is shown | No fabricated chart |
| nullable field null | evaluation | `evaluation=null` | Evaluation unavailable | `st.info` no interval inferred | No fake interval |
| nullable field null | confidence | `confidence=null` | Confidence not computed | `—` plus insufficient note | No 0% |
| nullable field null | lifecycle points | `points=null` | Not enough trajectory points | State still shown if present | No numeric substitution |

## Lifecycle Ground Truth

| Profile | Constructed truth | Correct M3 state |
| --- | --- | --- |
| `constant` | 0.6309 -> 0.6318, time-invariant | `stable` |
| `linear_decay` | 0.5918 -> 0.2767, monotone fading | `decaying` |
| `regime_off` | 0.6309 -> 0.2125, stops late | `decaying` |
| `regime_late` | 0.2294 -> 0.6318, starts late | `strengthening` |
| `intermittent` | 0.4864 -> 0.4181, alternating but present late | `stable` |

Decaying/dead are descriptive lifecycle states, not errors. The Streamlit tone
stays muted/warn and must not use red alert styling.

Lifecycle labels must never appear alone. They must be paired with the relation
`stability` value wherever the UI gives them visual weight. This prevents
`stable` from reading as "always continuously present" in cases like
`intermittent`, where the selected enum is valid but the lower stability value
is the evidence that the relation was present unevenly.

## Relationship Map Decision

Decision: for M3, the sorted evidence table is the primary report view and the
relationship map is secondary.

Reason: the current data shape is one target and four candidate signals. A
four-edge star makes the evidence look toy-sized in an investor demo even when
the evidence table is doing real work. This still honors W0 section 7 because
the relation map remains a required secondary view in the specification, but it
does not carry the main interpretive burden until candidate counts grow.

Future frontend encoding:

| Field | Encoding semantics | Streamlit implementation | Degradation |
| --- | --- | --- | --- |
| `selected` | Inclusion | Sort selected first; expander open for selected | Table remains canonical |
| `effect.score` | Edge width / evidence table score | Numeric score column | No edge-width encoding in Streamlit |
| `prediction_confidence.confidence` | Opacity/confidence | Confidence metric | No opacity encoding in Streamlit |
| `lifecycle.state` | Color/state | Badge tone and lifecycle track | Unknown state neutral |
| `trajectory` | Sparkline/timeline | Dated line chart in expander | Missing -> no chart caption |
| `decaying/dead` | Fading relation state | Warn/muted tone, descriptive text | No red alarm |
| null evidence | Unknown texture | Dash plus insufficient note | No texture in Streamlit |
