# S10 Evidence Gate and Prediction Confidence v0

Scope: S10 only. Evidence Gate consumes relation evidence; Prediction Confidence is reported separately and does not feed back into selection.

Selection inputs: effect size against the S8 noise floor, S9 stability, relationship uncertainty, sample support, and FDR correction across relations/lags.

Forbidden path remains absent: prediction error is not an input to selection.

## Fixture D: Selection Quality

- Seeds: `100`
- Fixed threshold precision mean: `0.262`
- Fixed threshold recall mean: `1.000`
- Evidence Gate precision mean: `1.000`
- Evidence Gate recall mean: `1.000`
- Precision lift: `0.738`
- Recall lift: `0.000`

## Prediction Confidence Calibration

- Spearman rank correlation, confidence vs absolute error: `-0.488`
- Lowest-confidence bin mean absolute error: `0.984`
- Highest-confidence bin mean absolute error: `0.255`

## Baseline Fallback

- No-evidence relation set fit status: `baseline_only_no_evidence`
