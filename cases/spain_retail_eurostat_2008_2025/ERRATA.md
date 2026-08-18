# Errata: `consumer_confidence` Column

The frozen `data.csv` column named `consumer_confidence` does not contain the
Eurostat consumer confidence indicator. Its values match the seasonally
adjusted construction confidence indicator:

- Dataset: `ei_bssi_m_r2`
- Indicator: `BS-CCI-BAL`
- Meaning: construction confidence indicator

The intended consumer confidence indicator is `BS-CSMCI-BAL`, whose values are
different. The frozen CSV, configuration, reports, and historical metrics are
not modified by this erratum. Any historical conclusion involving the column
named `consumer_confidence` must instead be understood as involving
construction confidence.

This correction is interpretive only. It does not retroactively change any
recorded number or establish causality.
