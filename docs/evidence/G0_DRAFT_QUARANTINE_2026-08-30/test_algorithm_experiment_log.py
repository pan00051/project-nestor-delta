from __future__ import annotations

import json
from pathlib import Path

from scripts import run_algorithm_experiment as exp


def test_judge_returns_rule_ids_and_fail_on_fpr_regression() -> None:
    verdict = exp.judge(
        detection_floor=0.35,
        false_positive_rate=0.15,
        max_detection_floor_abs_r=0.60,
        max_false_positive_rate=0.10,
    )

    assert verdict["outcome"] == "FAIL"
    assert {rule["rule_id"] for rule in verdict["rules"]} == {
        "AEXP-V1-R2",
        "AEXP-V1-R3",
    }


def test_judge_passes_when_floor_and_fpr_are_inside_bounds() -> None:
    verdict = exp.judge(
        detection_floor=0.35,
        false_positive_rate=0.05,
        max_detection_floor_abs_r=0.60,
        max_false_positive_rate=0.10,
    )

    assert verdict["outcome"] == "PASS"
    assert all(rule["status"] == "PASS" for rule in verdict["rules"])


def test_judge_fails_when_detection_floor_is_absent() -> None:
    verdict = exp.judge(
        detection_floor=None,
        false_positive_rate=0.0,
        max_detection_floor_abs_r=0.60,
        max_false_positive_rate=0.10,
    )

    assert verdict["outcome"] == "FAIL"
    assert verdict["rules"][0]["rule_id"] == "AEXP-V1-R1"


def test_append_jsonl_writes_one_compact_row(tmp_path: Path) -> None:
    path = tmp_path / "logs" / "experiments.jsonl"
    row = {"criteria_version": exp.CRITERIA_VERSION, "verdict": {"outcome": "PASS"}}

    exp.append_jsonl(path, row)

    lines = path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    assert json.loads(lines[0]) == row


def test_default_snapshot_id_changes_when_params_change() -> None:
    manifest = {
        "spec": {"seed_positive": 1},
        "fixtures": {"a": {"sha256": "abc"}},
        "sweep": {"b": {"sha256": "def"}},
    }

    one = exp.default_snapshot_id(manifest, {"seed_set": "tuning"})
    two = exp.default_snapshot_id(manifest, {"seed_set": "holdout"})

    assert one.startswith("ground_truth.")
    assert two.startswith("ground_truth.")
    assert one != two
