from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from statistics import mean

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from nestor_delta.config import (  # noqa: E402
    FEATURE_COLUMNS,
    LAG_WINDOW,
    TEST_LABEL_ROWS,
)
from nestor_delta.dynamic_prediction import (  # noqa: E402
    fit_dynamic_drift_predictor,
    fit_static_drift_predictor,
    predict_dynamic_drift,
    predict_static_drift,
)
from nestor_delta.dynamic_weights import (  # noqa: E402
    compute_rolling_relation_weights,
    target_source_trajectory,
)
from nestor_delta.metrics import mae, rmse  # noqa: E402
from nestor_delta.s4_config import (  # noqa: E402
    DRIFT_SEEDS,
    DYNAMIC_TRAIN_LABEL_ROWS,
    DYNAMIC_WINDOW,
)
from nestor_delta.synthetic_drift import (  # noqa: E402
    driver_a_coefficient,
    generate_drift_series,
    generate_drift_truth,
    write_drift_series_csv,
    write_drift_truth_csv,
)


class DriftSyntheticTests(unittest.TestCase):
    def test_frozen_coefficient_boundaries(self) -> None:
        self.assertEqual(driver_a_coefficient(0), 0.15)
        self.assertEqual(driver_a_coefficient(419), 0.15)
        self.assertEqual(driver_a_coefficient(420), 0.15)
        self.assertAlmostEqual(
            driver_a_coefficient(510),
            0.15 + 0.50 * (510 - 420) / 179,
        )
        self.assertEqual(driver_a_coefficient(599), 0.65)

    def test_same_seed_writes_identical_data_and_truth_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first_data = root / "first_data.csv"
            second_data = root / "second_data.csv"
            first_truth = root / "first_truth.csv"
            second_truth = root / "second_truth.csv"

            write_drift_series_csv(generate_drift_series(101), first_data)
            write_drift_series_csv(generate_drift_series(101), second_data)
            write_drift_truth_csv(generate_drift_truth(), first_truth)
            write_drift_truth_csv(generate_drift_truth(), second_truth)

            self.assertEqual(first_data.read_bytes(), second_data.read_bytes())
            self.assertEqual(first_truth.read_bytes(), second_truth.read_bytes())


class DynamicWeightTests(unittest.TestCase):
    def test_rolling_window_excludes_current_and_future_rows(self) -> None:
        rows = generate_drift_series(101)
        changed = [dict(row) for row in rows]
        changed[510]["target"] += 1000.0
        changed[599]["target"] -= 1000.0

        original = compute_rolling_relation_weights(
            rows, FEATURE_COLUMNS, LAG_WINDOW, (510,), DYNAMIC_WINDOW
        )
        after_change = compute_rolling_relation_weights(
            changed, FEATURE_COLUMNS, LAG_WINDOW, (510,), DYNAMIC_WINDOW
        )

        self.assertEqual(original, after_change)
        self.assertTrue(all(weight.window_end == 510 for weight in original))
        self.assertTrue(all(weight.window_start == 390 for weight in original))

    def test_dynamic_weights_track_drift_and_improve_prediction(self) -> None:
        static_maes = []
        dynamic_maes = []
        static_rmses = []
        dynamic_rmses = []

        for seed in DRIFT_SEEDS:
            rows = generate_drift_series(seed)
            labels = [float(rows[index]["target"]) for index in TEST_LABEL_ROWS]
            static_model = fit_static_drift_predictor(
                rows, DYNAMIC_TRAIN_LABEL_ROWS
            )
            dynamic_model = fit_dynamic_drift_predictor(
                rows, DYNAMIC_TRAIN_LABEL_ROWS
            )
            static_predictions = predict_static_drift(
                rows, TEST_LABEL_ROWS, static_model
            )
            dynamic_predictions, timed_weights = predict_dynamic_drift(
                rows, TEST_LABEL_ROWS, dynamic_model
            )

            trajectory = target_source_trajectory(
                timed_weights, "target", "driver_a"
            )
            self.assertGreater(trajectory[-1].weight, trajectory[0].weight)

            static_maes.append(mae(labels, static_predictions))
            dynamic_maes.append(mae(labels, dynamic_predictions))
            static_rmses.append(rmse(labels, static_predictions))
            dynamic_rmses.append(rmse(labels, dynamic_predictions))

        self.assertLess(mean(dynamic_maes), mean(static_maes))
        self.assertLess(mean(dynamic_rmses), mean(static_rmses))


if __name__ == "__main__":
    unittest.main()
