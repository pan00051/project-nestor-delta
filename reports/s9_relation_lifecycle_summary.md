# S9 Temporal Stability and Relation Lifecycle

Scope: S9 only. Stability and lifecycle are computed from S7 transformed rolling relation trajectories, not from legacy level Pearson scores.

No S10 Evidence Gate, Prediction Confidence, or prediction-error feedback into selection is implemented here.

## Relation Object v1

`RelationWeight` keeps existing `source, target, lag, weight, score, sample_count, transform` fields and adds only `stability`, `uncertainty`, and `selected`.

The `selected` field is nullable in S9. This report does not infer model selection.

## Fixture C: Relation Death Detection

- Seeds: `100`
- Known death step: `120`
- K-step window: `30`
- Detected within K: `100/100`
- Median detection lag: `14.5`
- Detection lag distribution: `1:1, 3:1, 4:2, 5:4, 6:6, 7:5, 8:7, 9:9, 10:1, 11:3, 12:1, 13:4, 14:6, 15:7, 16:4, 17:3, 18:7, 19:4, 20:2, 21:2, 22:7, 23:1, 24:4, 25:2, 27:2, 28:1, 29:3, 30:1`

## Fixture A Regression

Independent random walks are measured through the S7 transformed path before S9 aggregation.

- Median stability: `0.082`
- P90 stability: `0.252`
- Max stability: `0.359`
- P(stability > 0.45): `0.0%`
- Lifecycle state distribution: `birth:88, dead:5, decaying:7`
- P(state in stable/strengthening): `0.0%`

## Lifecycle States

`birth -> strengthening -> stable -> decaying -> dead` is implemented in `temporal_stability.py` from relation-score trajectory shape only.
