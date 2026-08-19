"""Static, honest presets. No fabricated Eurostat catalog or search results.

There is no Eurostat catalog/search API wired in, so the UI offers a manual
dataset/filter editor plus these verified presets only. Nothing here pretends to
be a live search.
"""

from __future__ import annotations

BUNDLED_CASES = (
    "spain_retail_eurostat_2008_2025",
    "spain_retail_eurostat_expanded_2008_2025",
    "spain_industrial_production_eurostat_2008_2023",
)

DEFAULT_CASE = "spain_retail_eurostat_2008_2025"

# One verified Eurostat preset. Manually authored, not fetched.
EUROSTAT_PRESETS = {
    "ES industry vs construction confidence (ei_bssi_m_r2)": {
        "target": "industry_confidence",
        "candidate_signals": ["construction_confidence"],
        "train_end": "2019-12",
        "lag_window": 3,
        "start": "2005-01",
        "end": "2023-12",
        "series": [
            {"name": "industry_confidence", "dataset": "ei_bssi_m_r2",
             "filters": {"freq": "M", "indic": "BS-ICI-BAL", "s_adj": "SA", "geo": "ES"}},
            {"name": "construction_confidence", "dataset": "ei_bssi_m_r2",
             "filters": {"freq": "M", "indic": "BS-CCI-BAL", "s_adj": "SA", "geo": "ES"}},
        ],
    },
}

TRANSFORMS = ("none", "diff", "log_diff")
