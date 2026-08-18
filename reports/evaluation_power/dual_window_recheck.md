# Dual-Window Recheck (frozen selection, rolling origin)

Faithful re-evaluation of the published dual-window result: the frozen
selected source set and lag are held fixed; only OLS coefficients are
refit on each origin's past-only window. No per-fold re-selection.

The published single-window numbers were `+7.11%` (Case B validation) and
`-9.63%` (Case B pandemic). Below, each is placed against the frozen
model's per-origin skill distribution.

## Case A (normal) — `spain_industrial_normal_2008_2021`

Frozen mode is `baseline_only`: the validation guard froze this case
to persistence, so the model IS the baseline and per-origin skill is
identically zero. There is no fitted relation to re-evaluate.

## Case B (shock) — `spain_industrial_shock_2008_2021`

Frozen selection: `unemployment_rate, retail_employment, industrial_turnover, construction_production, domestic_energy_producer_prices` at lag `3`.

- Validation-era block skill (my refit): `+7.11%` (published `+7.11%`).
- Pandemic block skill (my refit): `-7.10%` (published `-9.63%`).

| Era | Origins | Per-origin median | 90% interval | Resolves? |
|---|---|---|---|---|
| validation | 24 | +11.46% | [-8.05%, +40.62%] | no |
| pandemic | 24 | -46.73% | [-75.72%, -7.57%] | yes |

**Interpretation.** The pandemic per-origin median (`-46.73%`) falls OUTSIDE the validation-era 90% band `[-8.05%, +40.62%]`. The pandemic block sits outside the ordinary band, consistent with a regime change rather than sampling noise.

Neither the validation-era nor the pandemic per-origin interval is uniformly unresolved; see the interval flags above.
