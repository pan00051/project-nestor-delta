# Data Scope and Honesty Boundary

This case uses an exact monthly axis from `2008-01` through `2023-12`
(192 months). No rows were deleted and no values were filled or interpolated.

The original request contained dataset or dimension codes that are unavailable
in the current Eurostat API. The substitutions below are explicit and must not
be read as silent equivalence.

| Role | Original requested scope | Actual scope used | Semantic boundary |
|---|---|---|---|
| Target | `sts_inpr_m; nace_r2=C; s_adj=SCA; unit=I15; geo=ES` | `sts_inpr_m; nace_r2=C; s_adj=SCA; unit=I15; geo=ES` | No substitution. This is the target manufacturing production volume index. |
| Signal 1 | `sts_inot_m; nace_r2=C; s_adj=SCA; unit=I15; geo=ES` | `ei_bsin_m_r2; indic=BS-IOB; s_adj=SA; unit=BAL; geo=ES` | SUBSTANTIVE CHANGE: the requested series was a quantitative index of actual industrial new orders. The used series is a seasonally adjusted survey balance of managers' assessment of current order-book levels. It measures sentiment about order books, not the quantity of new orders, and must not be interpreted as an equivalent replacement. |
| Signal 2 | `ei_bsin_m_r2; indic=BS-IND-PO; s_adj=SA; geo=ES` | `ei_bsin_m_r2; indic=BS-IPE; s_adj=SA; unit=BAL; geo=ES` | The requested indicator code is not present in the current dataset. BS-IPE is the current Eurostat code for production expectations over the next three months. |
| Signal 3 | `sts_inppd_m; nace_r2=C19-C20; s_adj=NSA; unit=I15; geo=ES` | `sts_inppd_m; nace_r2=MIG_NRG; s_adj=NSA; unit=I15; geo=ES` | C19-C20 is not a current NACE aggregate in this dataset. MIG_NRG is the available Main Industrial Grouping for energy and is broader than a simple combination of coke/refined petroleum and chemicals. |
| Signal 4 | `ei_bsin_m_r2; indic=BS-IND-EMPE; s_adj=SA; geo=ES` | `ei_bsin_m_r2; indic=BS-IEME-BAL; s_adj=SA; unit=BAL; geo=ES` | The requested indicator code is not present in the current dataset. BS-IEME-BAL is the current industry employment-expectations balance for the next three months. |

## Critical Difference: New Orders vs Order-Book Assessment

The originally requested industrial new-orders series was a quantitative
index intended to represent actual new-order volume. The actual
`BS-IOB` series is a qualitative, seasonally adjusted survey balance: it
summarises managers' assessments of current order-book levels. It does not
measure the quantity of newly received orders. Any result involving this
signal must therefore be described as association with reported order-book
sentiment, not association with actual new-order volume.

This distinction is part of Delta's honesty boundary and must remain visible
in reports or portfolio material derived from this case.
