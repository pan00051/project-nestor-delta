"""Regression tests for the frozen Sprint 1 data and baseline pipeline."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from nestor_delta.baselines import fit_linear_regression  # noqa: E402
from nestor_delta.config import FEATURE_COLUMNS, TRAIN_LABEL_ROWS  # noqa: E402
from nestor_delta.splits import build_lagged_samples  # noqa: E402
from nestor_delta.synthetic import generate_series, write_series_csv  # noqa: E402


def feature_names() -> list[str]:
    names = ["intercept"]
    for lag in range(1, 6):
        names.extend(f"{column}_lag{lag}" for column in FEATURE_COLUMNS)
    return names


class Sprint1ReproducibilityTests(unittest.TestCase):
    def test_same_seed_writes_identical_csv_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            first_path = Path(tmpdir) / "first.csv"
            second_path = Path(tmpdir) / "second.csv"

            write_series_csv(generate_series(11), first_path)
            write_series_csv(generate_series(11), second_path)

            self.assertEqual(first_path.read_bytes(), second_path.read_bytes())

    def test_ols_recovers_known_synthetic_drivers(self) -> None:
        rows = generate_series(11)
        features, labels = build_lagged_samples(rows, TRAIN_LABEL_ROWS)
        coefficients = fit_linear_regression(features, labels)
        by_name = dict(zip(feature_names(), coefficients))

        self.assertAlmostEqual(by_name["driver_a_lag1"], 0.35, delta=0.10)
        self.assertAlmostEqual(by_name["driver_b_lag2"], -0.25, delta=0.10)
        self.assertAlmostEqual(by_name["target_lag1"], 0.55, delta=0.10)

        true_driver_names = {"driver_a_lag1", "driver_b_lag2", "target_lag1"}
        other_coefficients = [
            abs(value)
            for name, value in by_name.items()
            if name != "intercept" and name not in true_driver_names
        ]
        self.assertLess(max(other_coefficients), 0.10)


if __name__ == "__main__":
    unittest.main()
