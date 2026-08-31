from __future__ import annotations

import base64
import json
from pathlib import Path

import pytest

from nestor_delta_service import adapter


FIXTURES = Path(__file__).parent / "ground_truth" / "fixtures"
MANIFEST = json.loads((FIXTURES / "manifest.json").read_text(encoding="utf-8"))
ROLLING_NEGATIVE = MANIFEST["q6"]["fixtures"]["s_gt_6_rolling_negative"]


def _payload(train_observations: int, lag_window: int) -> dict:
    lines = (FIXTURES / ROLLING_NEGATIVE["file"]).read_text(
        encoding="utf-8"
    ).splitlines()
    payload = dict(ROLLING_NEGATIVE["request"])
    payload["lag_window"] = lag_window
    payload["train_end"] = lines[train_observations].split(",", 1)[0]
    payload["csv_base64"] = base64.b64encode(
        ("\n".join(lines[: train_observations + 1]) + "\n").encode("utf-8")
    ).decode("ascii")
    return payload


def _assert_audit_analyze_consistent(
    audit_result: tuple[int, dict], analyze_result: tuple[int, dict]
) -> None:
    audit_status, audit_report = audit_result
    analyze_status, analyze_report = analyze_result
    audit_accepts = (
        audit_status == 200 and audit_report.get("outcome") == "ok_to_analyze"
    )
    assert not (audit_accepts and analyze_status == 422), analyze_report


def _warning_codes(report: dict) -> set[str]:
    return {
        warning.get("code")
        for warning in report.get("warnings") or []
        if isinstance(warning, dict) and warning.get("code")
    }


def test_g8_positive_control_reproduces_the_legacy_empty_trajectory_gap(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def legacy_entry_condition(analysis_input, train_rows) -> bool:
        return len(train_rows) > analysis_input.lag_window + 8

    monkeypatch.setattr(
        adapter,
        "_rolling_lifecycle_available",
        legacy_entry_condition,
    )
    payload = _payload(train_observations=12, lag_window=3)
    audit_result = adapter.audit_payload(payload)
    analyze_result = adapter.analyze_payload(payload)

    assert audit_result[0] == 200
    assert analyze_result[0] == 422
    assert analyze_result[1]["error"]["message"] == (
        "trajectory must contain at least one point"
    )
    with pytest.raises(AssertionError):
        _assert_audit_analyze_consistent(audit_result, analyze_result)


@pytest.mark.parametrize(
    ("lag_window", "train_observations", "stability_evaluated"),
    [
        (3, 11, False),
        (3, 12, False),
        (3, 13, True),
        (3, 14, True),
        (6, 16, False),
        (6, 19, True),
    ],
)
def test_g8_audit_acceptance_is_analyzable_and_warning_is_honest(
    lag_window: int,
    train_observations: int,
    stability_evaluated: bool,
) -> None:
    payload = _payload(train_observations, lag_window)
    audit_result = adapter.audit_payload(payload)
    analyze_result = adapter.analyze_payload(payload)

    _assert_audit_analyze_consistent(audit_result, analyze_result)
    audit_status, audit_report = audit_result
    analyze_status, report = analyze_result
    assert (audit_status, audit_report["outcome"]) == (200, "ok_to_analyze")
    assert analyze_status == 200
    assert report["outcome"] in {"ok", "baseline_only"}

    warning_codes = _warning_codes(report)
    if stability_evaluated:
        assert "stability_not_evaluated" not in warning_codes
        assert report["configuration"]["rolling_lifecycle"]["effective_window"] is not None
    else:
        assert "stability_not_evaluated" in warning_codes
        assert report["configuration"]["rolling_lifecycle"]["effective_window"] is None
        assert all(relation["stability"] is None for relation in report["relations"])
        warning = next(
            warning
            for warning in report["warnings"]
            if warning.get("code") == "stability_not_evaluated"
        )
        assert str(train_observations) in warning["message"]
        assert "at least" in warning["message"]
