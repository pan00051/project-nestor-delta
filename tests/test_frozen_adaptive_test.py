from __future__ import annotations

import csv
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from nestor_delta.frozen_adaptive_test import (  # noqa: E402
    FrozenAdaptiveSelection,
    run_frozen_test_once,
    write_frozen_test_reports,
)
from nestor_delta.real_data import RealCaseData  # noqa: E402
from nestor_delta.validation_parameter_search import AdaptiveCaseSpec  # noqa: E402


class FrozenAdaptiveTestTests(unittest.TestCase):
    def test_baseline_guard_leaves_delta_fields_empty(self) -> None:
        spec, data = _fixture()
        selection = FrozenAdaptiveSelection(
            case_name=spec.case_name,
            final_mode="baseline_only",
            relation_threshold=0.5,
            lag_window=1,
            max_selected_signals=1,
            baseline_guard_applied=True,
        )
        result = run_frozen_test_once(spec, data, selection)
        self.assertIsNone(result.delta_mae)
        self.assertTrue(all(value is None for value in result.delta_predictions))
        with tempfile.TemporaryDirectory() as directory:
            paths = write_frozen_test_reports(
                Path(directory), spec, selection, result
            )
            with paths[0].open(newline="", encoding="utf-8") as handle:
                metric = next(csv.DictReader(handle))
            self.assertEqual(metric["delta_mae"], "")
            self.assertEqual(metric["parameters_adjusted_after_test"], "false")

    def test_delta_path_refits_and_predicts_test(self) -> None:
        spec, data = _fixture()
        selection = FrozenAdaptiveSelection(
            case_name=spec.case_name,
            final_mode="delta",
            relation_threshold=0.0,
            lag_window=1,
            max_selected_signals=1,
            baseline_guard_applied=False,
        )
        result = run_frozen_test_once(spec, data, selection)
        self.assertEqual(result.fit_status, "fit")
        self.assertEqual(result.selected_sources, ("signal",))
        self.assertIsNotNone(result.delta_mae)
        self.assertTrue(all(value is not None for value in result.delta_predictions))


def _fixture():
    dates = []
    rows = []
    year, month = 2008, 1
    target = 10.0
    for index in range(60):
        dates.append(f"{year:04d}-{month:02d}")
        signal = float(index % 7) + index * 0.1
        target = 0.75 * target + 0.8 * signal + 2.0
        rows.append({"target": target, "signal": signal})
        month += 1
        if month == 13:
            month = 1
            year += 1
    spec = AdaptiveCaseSpec(
        case_name="toy",
        csv_path=Path("unused.csv"),
        date_column="date",
        target="target",
        candidate_signals=("signal",),
        train_start="2008-01",
        train_end="2009-12",
        validation_start="2010-01",
        validation_end="2010-12",
        test_start="2011-01",
        test_end="2011-12",
        relation_thresholds=(0.0,),
        lag_windows=(1,),
        max_selected_signals=(1,),
        output_dir=Path("unused"),
        notes="",
    )
    data = RealCaseData(
        dates=tuple(dates),
        rows=tuple(rows),
        variables=("target", "signal"),
    )
    return spec, data


if __name__ == "__main__":
    unittest.main()
