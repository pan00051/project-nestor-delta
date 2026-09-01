# Known Limitations

These limits qualify public interpretation of the current demo. They do not
change Report JSON or the frozen evidence-gate thresholds.

## Calibration-only real-data result

`spain_industrial_shock_2008_2021` can produce `outcome: ok`, but it is a
calibration case rather than independent evidence. Its `lag_window=3` was
selected by a parameter search that minimized validation MAE on the same case.
The result may be shown only with that qualification and is not the bundled
positive demo case.

The selected `employment_expectations -> industrial_production` relation is
close to the current selection boundary: stability is `0.4737`, only `0.0237`
above `min_stability=0.45`. Its score, `0.2095`, is about `59.6%` of the measured
detection boundary `0.3518`, and its `effect_size_vs_noise_floor` is `0.709`, so
the full-window effect is below its own diagnostic noise floor.

## Full-window sign can contradict the trajectory

The same relation reports full-window `effect.sign: +1`, `lifecycle: stable`,
and stability `0.4737`, while 11 of its 14 rolling trajectory points have sign
`-1`; the last seven are continuously negative and rise overall in magnitude
from `0.178` to `0.571`, with one dip from `0.478` to `0.437`. The Report also
gives lag `2`, while 10 of 14 rolling argmax lags are `3`.

This is H-11. Until the post-M5 repair is evaluated, consumers of downloaded
Report JSON must not treat the headline sign, lag, or `stable` label as a
summary of rolling sign and lag agreement. Candidate repairs are to include
sign consistency in stability, or to prohibit `stable` and emit an explicit
warning when the trajectory's majority sign contradicts the full-window sign.
