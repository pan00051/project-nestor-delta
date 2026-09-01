from __future__ import annotations

from pathlib import Path

from nestor_delta_service.adapter import SUPPORTED_CASES, analyze_payload


REPO_ROOT = Path(__file__).resolve().parents[1]
POSITIVE_CASE = "synthetic_ground_truth_calibration_control"


def _analyze_case(case_name: str) -> dict:
    status, report = analyze_payload({"case_name": case_name})
    assert status == 200, (case_name, report.get("error"))
    return report


def test_g9_at_least_one_bundled_case_produces_selected_relation() -> None:
    passing = []
    for case_name in SUPPORTED_CASES:
        report = _analyze_case(case_name)
        if report["outcome"] == "ok" and report["selection"]["selected_count"] >= 1:
            passing.append(case_name)

    assert passing, "G9: no bundled case produces outcome=ok with a selected relation"


def test_bundled_ground_truth_case_recovers_injected_relation() -> None:
    report = _analyze_case(POSITIVE_CASE)
    selected = [relation for relation in report["relations"] if relation["selected"]]

    assert report["outcome"] == "ok"
    assert report["selection"]["selected_count"] == 1
    assert report["selection"]["selected_sources"] == ["true_driver"]
    assert len(selected) == 1
    assert selected[0]["source"] == "true_driver"
    assert selected[0]["lag"] == 2
    assert selected[0]["effect"]["sign"] == -1


def test_bundled_ground_truth_data_is_byte_identical_to_frozen_fixture() -> None:
    fixture = REPO_ROOT / "tests" / "ground_truth" / "fixtures" / "s_gt_1_positive.csv"
    bundled = REPO_ROOT / "cases" / POSITIVE_CASE / "data.csv"

    assert bundled.read_bytes() == fixture.read_bytes()
