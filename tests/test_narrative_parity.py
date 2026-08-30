"""Keep report narrative examples pinned to the adapter's output."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from nestor_delta_service.adapter import _narrative


REPO = Path(__file__).resolve().parents[1]
MOCKS = json.loads((REPO / "docs" / "mock_reports_v1.json").read_text(encoding="utf-8"))


def test_mock_report_headlines_match_adapter_narrative() -> None:
    checked = []
    for name, report in MOCKS.items():
        if not isinstance(report, dict) or "narrative" not in report:
            continue
        outcome = report.get("outcome")
        if outcome not in {"ok", "baseline_only"}:
            continue
        relation_count = len(report.get("relations") or [])
        selected_count = int((report.get("selection") or {}).get("selected_count") or 0)
        gate = SimpleNamespace(selected_relations=tuple(range(selected_count)))

        expected = _narrative(outcome, gate, relation_count)["headline"]

        assert report["narrative"]["headline"] == expected, name
        checked.append(name)

    assert checked == ["baseline_only__spain_retail", "ok__with_selection"]
