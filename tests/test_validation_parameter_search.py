from __future__ import annotations

import csv
import json
import tempfile
import unittest
import sys
from dataclasses import replace
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from nestor_delta.real_data import RealCaseData
from nestor_delta.validation_parameter_search import (
    load_adaptive_case,
    run_validation_parameter_search,
    write_validation_search_reports,
)


CASE_PATH = ROOT / "cases" / "spain_industrial_normal_2008_2021" / "adaptive_case.json"


class ValidationParameterSearchTests(unittest.TestCase):
    def test_declared_grid_and_test_isolation(self) -> None:
        spec, data = load_adaptive_case(CASE_PATH)
        original = run_validation_parameter_search(spec, data)
        changed_rows = []
        for date, row in zip(data.dates, data.rows):
            changed = dict(row)
            if spec.test_start <= date <= spec.test_end:
                for offset, name in enumerate(sorted(changed), start=1):
                    changed[name] += 10000.0 * offset
            changed_rows.append(changed)
        changed_data = RealCaseData(data.dates, tuple(changed_rows), data.variables)
        changed = run_validation_parameter_search(spec, changed_data)

        self.assertEqual(len(original.rows), 150)
        self.assertEqual(original, changed)

    def test_reports_are_byte_identical_and_mark_test_false(self) -> None:
        spec, data = load_adaptive_case(CASE_PATH)
        result = run_validation_parameter_search(spec, data)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = write_validation_search_reports(
                replace(spec, output_dir=root / "first"), result
            )
            second = write_validation_search_reports(
                replace(spec, output_dir=root / "second"), result
            )
            for left, right in zip(first, second):
                self.assertEqual(left.read_bytes(), right.read_bytes())
                self.assertIn(b"test_evaluated", left.read_bytes())
                self.assertNotIn(b"test_mae", left.read_bytes())

    def test_physical_column_order_does_not_change_search(self) -> None:
        spec, data = load_adaptive_case(CASE_PATH)
        expected = run_validation_parameter_search(spec, data)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            payload = json.loads(CASE_PATH.read_text(encoding="utf-8"))
            source_csv = CASE_PATH.parent / payload["csv"]
            with source_csv.open(newline="", encoding="utf-8") as handle:
                source_rows = list(csv.DictReader(handle))
            fieldnames = list(reversed(list(source_rows[0])))
            reordered_csv = root / "data.csv"
            with reordered_csv.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(
                    handle, fieldnames=fieldnames, lineterminator="\n"
                )
                writer.writeheader()
                writer.writerows(source_rows)
            payload["csv"] = "data.csv"
            payload["output_dir"] = "reports"
            config_path = root / "adaptive_case.json"
            config_path.write_text(
                json.dumps(payload, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            changed_spec, changed_data = load_adaptive_case(config_path)
            changed = run_validation_parameter_search(changed_spec, changed_data)
            self.assertEqual(expected, changed)


if __name__ == "__main__":
    unittest.main()
