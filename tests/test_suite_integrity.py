"""Guard the test harness itself.

These checks make a green test run prove that the ground-truth suite was
available and that the registered minimum collection count still holds.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]


def test_pytest_configuration_collects_ground_truth_suite() -> None:
    text = (REPO / "pyproject.toml").read_text(encoding="utf-8")

    assert re.search(r'pythonpath\s*=\s*\[[^\]]*"src"[^\]]*\]', text)
    assert re.search(r'pythonpath\s*=\s*\[[^\]]*"tests/ground_truth"[^\]]*\]', text)
    assert 'testpaths = ["tests"]' in text


def test_known_ground_truth_test_is_importable() -> None:
    import test_ground_truth

    assert hasattr(test_ground_truth, "test_sgt2b_false_positive_rate_across_seeds")


def test_pytest_collection_count_meets_registered_floor() -> None:
    baseline = _registered_collection_floor()
    env = dict(os.environ)
    env["NESTOR_SUITE_INTEGRITY_COLLECT"] = "1"

    result = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q", "tests"],
        cwd=REPO,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )

    collected = _collection_count(result.stdout + result.stderr)
    assert collected >= baseline


def _registered_collection_floor() -> int:
    text = (REPO / "docs" / "DEFECT_LEDGER.md").read_text(encoding="utf-8")
    rows = re.findall(r"\|\s*\d{4}-\d{2}-\d{2}\s*\|\s*`[^`]+`\s*\|\s*(\d+)\s*\|", text)
    assert rows, "DEFECT_LEDGER.md collection baseline row is missing"
    return int(rows[-1])


def _collection_count(output: str) -> int:
    match = re.search(r"(\d+)\s+tests?\s+collected", output)
    assert match, output
    return int(match.group(1))
