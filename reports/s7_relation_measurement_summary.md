# S7 Relation Measurement Summary

Scope: S7 only. Legacy level Pearson scoring is preserved as the control path; S7 transformed scoring measures explicit short-run transformed relationships only.

## Synthetic Fixtures

| Fixture | Path | Seeds | Median abs r | P90 abs r | P(abs r > 0.06) | P(abs r > 0.30) | Correct lag |
|---|---|---:|---:|---:|---:|---:|---:|
| fixture_a_random_walk | legacy_level_scoring | 500 | 0.410 | 0.772 | 93.6% | 66.4% | n/a |
| fixture_a_random_walk | s7_transformed_diff | 500 | 0.088 | 0.140 | 76.0% | 0.0% | n/a |
| fixture_b_trended_dynamic | legacy_level_scoring | 200 | 0.973 | 0.991 | 100.0% | 99.5% | n/a |
| fixture_b_trended_dynamic | s7_transformed_diff | 200 | 0.598 | 0.650 | 100.0% | 100.0% | 100.0% |

Fixture A shows the old level path admitting independent random walks while the transformed path removes the high-score pseudo relationship. Fixture B keeps the true short-run dynamic relation and recovers lag 3 in every seed.

## Eurostat Diagnostics

The `highly_persistent_risk` column is only a lag-1 ACF risk flag. It is not an ADF/KPSS result and is not reported as a formal stationarity conclusion.

| Case | Signal | Transform | lag-1 ACF | Risk flag |
|---|---|---|---:|---|
| spain_retail_eurostat_2008_2025 | hicp | diff | 0.992 | True |
| spain_retail_eurostat_2008_2025 | unemployment_rate | diff | 0.998 | True |
| spain_industrial_production_eurostat_2008_2023 | domestic_energy_producer_prices | diff | 0.967 | True |
| spain_industrial_production_eurostat_2008_2023 | order_book_assessment | diff | 0.967 | True |
| spain_retail_eurostat_expanded_2008_2025 | hicp | diff | 0.992 | True |
| spain_retail_eurostat_expanded_2008_2025 | industrial_turnover | diff | 0.966 | True |
| spain_retail_eurostat_expanded_2008_2025 | retail_employment | diff | 0.995 | True |
| spain_retail_eurostat_expanded_2008_2025 | unemployment_rate | diff | 0.998 | True |
| spain_industrial_normal_2008_2021 | industrial_production | diff | 0.983 | True |
| spain_industrial_normal_2008_2021 | domestic_energy_producer_prices | diff | 0.980 | True |
| spain_industrial_normal_2008_2021 | hicp | diff | 0.972 | True |
| spain_industrial_normal_2008_2021 | industrial_turnover | diff | 0.954 | True |
| spain_industrial_normal_2008_2021 | order_book_assessment | diff | 0.965 | True |
| spain_industrial_normal_2008_2021 | retail_employment | diff | 0.999 | True |
| spain_industrial_normal_2008_2021 | unemployment_rate | diff | 0.999 | True |
| spain_industrial_shock_2008_2021 | industrial_production | diff | 0.981 | True |
| spain_industrial_shock_2008_2021 | consumer_confidence | diff | 0.978 | True |
| spain_industrial_shock_2008_2021 | domestic_energy_producer_prices | diff | 0.968 | True |
| spain_industrial_shock_2008_2021 | economic_sentiment | diff | 0.980 | True |
| spain_industrial_shock_2008_2021 | employment_expectations | diff | 0.962 | True |
| spain_industrial_shock_2008_2021 | hicp | diff | 0.970 | True |
| spain_industrial_shock_2008_2021 | industry_confidence | diff | 0.971 | True |
| spain_industrial_shock_2008_2021 | order_book_assessment | diff | 0.986 | True |
| spain_industrial_shock_2008_2021 | retail_employment | diff | 0.998 | True |
| spain_industrial_shock_2008_2021 | services_confidence | diff | 0.972 | True |
| spain_industrial_shock_2008_2021 | unemployment_rate | diff | 0.998 | True |

## Spain And Dual-Window Top Relations

Both paths are reported side by side; no case is selected or promoted based on the nicer result.

| Case | Path | Top source | Lag | Weight | Score | Transform |
|---|---|---|---:|---:|---:|---|
| spain_retail_eurostat_2008_2025 | legacy_level_scoring | industrial_production | 1 | 0.791 | 0.791 | none |
| spain_retail_eurostat_2008_2025 | s7_transformed_scoring | industrial_production | 2 | -0.355 | 0.355 | diff |
| spain_industrial_production_eurostat_2008_2023 | legacy_level_scoring | domestic_energy_producer_prices | 3 | -0.357 | 0.357 | none |
| spain_industrial_production_eurostat_2008_2023 | s7_transformed_scoring | domestic_energy_producer_prices | 1 | 0.163 | 0.163 | diff |
| spain_retail_eurostat_expanded_2008_2025 | legacy_level_scoring | retail_employment | 1 | 0.793 | 0.793 | none |
| spain_retail_eurostat_expanded_2008_2025 | s7_transformed_scoring | industrial_production | 2 | -0.355 | 0.355 | diff |
| spain_industrial_normal_2008_2021 | legacy_level_scoring | unemployment_rate | 1 | -0.930 | 0.930 | none |
| spain_industrial_normal_2008_2021 | s7_transformed_scoring | industry_employment_expectations | 1 | 0.448 | 0.448 | diff |
| spain_industrial_shock_2008_2021 | legacy_level_scoring | unemployment_rate | 1 | -0.926 | 0.926 | none |
| spain_industrial_shock_2008_2021 | s7_transformed_scoring | order_book_assessment | 1 | 0.423 | 0.423 | diff |

## Boundaries

- Transform declarations are explicit case inputs: `none`, `diff`, or `log_diff`; the diagnostics do not choose transforms.
- S7 does not implement cointegration, ECM/VECM, long-run relationships, temporal stability, evidence gates, prediction confidence, nonlinear scoring, FFT, or coherence.
- Real-data prediction accuracy is not the S7 acceptance criterion.
