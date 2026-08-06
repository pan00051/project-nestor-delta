#!/usr/bin/env python3
"""Run the additive real-case S5-to-S6 budget sweep connector."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from nestor_delta.real_budget_sweep import (  # noqa: E402
    run_real_budget_sweep,
    write_real_budget_sweep_reports,
)
from nestor_delta.real_data import (  # noqa: E402
    load_real_case_config,
    load_real_case_data,
)


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(
            "Usage: python scripts/run_real_budget_sweep.py "
            "cases/<case_name>/case.json"
        )
        return 2

    config = load_real_case_config(Path(argv[1]))
    data = load_real_case_data(config)
    result = run_real_budget_sweep(config, data)
    paths = write_real_budget_sweep_reports(
        config.output_dir, config, data, result
    )
    for path in paths:
        print(f"Wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
