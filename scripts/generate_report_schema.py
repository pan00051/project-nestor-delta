#!/usr/bin/env python3
"""Generate the committed Report JSON v1 schema artifact."""

from __future__ import annotations

import json
from pathlib import Path

from nestor_delta_service.schema import report_json_schema


def main() -> None:
    path = Path("docs/report_json_v1.schema.json")
    path.write_text(
        json.dumps(report_json_schema(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {path}")


if __name__ == "__main__":
    main()
