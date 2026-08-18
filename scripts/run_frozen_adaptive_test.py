#!/usr/bin/env python3
"""Run one validation-frozen adaptive test evaluation."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from nestor_delta.frozen_adaptive_test import (  # noqa: E402
    load_frozen_selection,
    run_frozen_test_once,
    write_frozen_test_reports,
)
from nestor_delta.validation_parameter_search import load_adaptive_case  # noqa: E402


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print(
            "Usage: run_frozen_adaptive_test.py "
            "cases/<name>/adaptive_case.json reports/<name>/validation_selection.json"
        )
        return 2
    spec, data = load_adaptive_case(Path(argv[1]))
    selection = load_frozen_selection(Path(argv[2]))
    result = run_frozen_test_once(spec, data, selection)
    for path in write_frozen_test_reports(spec.output_dir, spec, selection, result):
        print(f"Wrote {path}")
    print("Parameters adjusted after test: false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
