"""Static, honest presets. No fabricated Eurostat catalog or search results.

There is no Eurostat catalog/search API wired in, so the UI offers a manual
dataset/filter editor plus these verified presets only. Nothing here pretends to
be a live search.
"""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

BUNDLED_CASES = (
    "synthetic_ground_truth_calibration_control",
    "spain_retail_eurostat_2008_2025",
    "spain_retail_eurostat_expanded_2008_2025",
    "spain_industrial_production_eurostat_2008_2023",
)

DEFAULT_CASE = "spain_retail_eurostat_2008_2025"
REPO_ROOT = Path(__file__).resolve().parents[2]

# One verified Eurostat preset. Manually authored, not fetched.
EUROSTAT_PRESETS = {
    "es_industry_vs_construction_confidence": {
        "id": "es_industry_vs_construction_confidence",
        "label": "ES industry vs construction confidence",
        "dataset": "ei_bssi_m_r2",
        "target": "industry_confidence",
        "candidate_signals": ["construction_confidence"],
        "train_end": "2019-12",
        "lag_window": 3,
        "start": "2005-01",
        "end": "2023-12",
        "snapshot_fixture": "fixtures/eurostat/ei_bssi_m_r2_es_industry_construction_2005_2023.json",
        "series": [
            {"name": "industry_confidence", "dataset": "ei_bssi_m_r2",
             "filters": {"freq": "M", "indic": "BS-ICI-BAL", "s_adj": "SA", "geo": "ES"}},
            {"name": "construction_confidence", "dataset": "ei_bssi_m_r2",
             "filters": {"freq": "M", "indic": "BS-CCI-BAL", "s_adj": "SA", "geo": "ES"}},
        ],
    },
}

TRANSFORMS = ("none", "diff", "log_diff")


def capability_presets() -> list[dict[str, str]]:
    return [
        {
            "id": str(preset["id"]),
            "label": str(preset["label"]),
            "dataset": str(preset["dataset"]),
        }
        for preset in EUROSTAT_PRESETS.values()
    ]


def preset_label(preset_id: str) -> str:
    preset = EUROSTAT_PRESETS[preset_id]
    return f"{preset['label']} ({preset['dataset']})"


def frozen_snapshot_payload(preset_id: str) -> dict[str, object]:
    preset = EUROSTAT_PRESETS[preset_id]
    fixture_path = REPO_ROOT / str(preset["snapshot_fixture"])
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    return deepcopy(fixture["snapshots"])
