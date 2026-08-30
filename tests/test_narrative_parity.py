"""Keep report narrative examples pinned to the adapter's output."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from nestor_delta_service.adapter import _narrative


REPO = Path(__file__).resolve().parents[1]
MOCKS = json.loads((REPO / "docs" / "mock_reports_v1.json").read_text(encoding="utf-8"))
W0 = (REPO / "docs" / "WEBSITE_CONTRACT_W0.md").read_text(encoding="utf-8")


def _baseline_headline() -> str:
    gate = SimpleNamespace(selected_relations=())
    return _narrative("baseline_only", gate, 4)["headline"]


def _assert_w0_baseline_headline_matches(w0_text: str) -> None:
    expected = f'"headline": "{_baseline_headline()}"'
    assert expected in w0_text


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


def test_w0_baseline_headline_matches_adapter_narrative() -> None:
    _assert_w0_baseline_headline_matches(W0)


def test_w0_headline_guard_rejects_in_memory_drift() -> None:
    drifted = W0.replace(_baseline_headline(), "Drifted headline", 1)

    with pytest.raises(AssertionError):
        _assert_w0_baseline_headline_matches(drifted)
