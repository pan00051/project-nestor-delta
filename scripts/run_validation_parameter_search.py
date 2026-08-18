#!/usr/bin/env python3
"""Run validation-only adaptive parameter search for one prepared case."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from nestor_delta.validation_parameter_search import (  # noqa: E402
    load_adaptive_case,
    run_validation_parameter_search,
    write_validation_search_reports,
)


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("Usage: run_validation_parameter_search.py cases/<name>/adaptive_case.json")
        return 2
    spec, data = load_adaptive_case(Path(argv[1]))
    result = run_validation_parameter_search(spec, data)
    for path in write_validation_search_reports(spec, result):
        print(f"Wrote {path}")
    selected = result.selected
    print(
        "Selected on validation only: "
        f"threshold={selected.relation_threshold:.2f}, "
        f"lag={selected.lag_window}, max_signals={selected.max_selected_signals}, "
        f"validation_mae={selected.validation_mae:.10f}, "
        f"fit_status={selected.fit_status}"
    )
    print("Test evaluated: false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
