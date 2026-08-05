from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from nestor_delta.config import SEEDS, TEST_LABEL_ROWS, TRAIN_LABEL_ROWS  # noqa: E402
from nestor_delta.metrics import mae, rmse  # noqa: E402
from nestor_delta.stage1_prediction import (  # noqa: E402
    fit_stage1_weighted_predictor,
    predict_stage1_weighted,
)
from nestor_delta.synthetic import generate_series  # noqa: E402


class Stage1PredictionTests(unittest.TestCase):
    def test_stage1_selects_two_known_driver_sources(self) -> None:
        rows = generate_series(11)
        model = fit_stage1_weighted_predictor(rows, TRAIN_LABEL_ROWS)
        selected_sources = [weight.source for weight in model.selected_weights]

        self.assertEqual(selected_sources, ["driver_a", "driver_b"])

    def test_stage1_is_deterministic_for_same_seed(self) -> None:
        rows = generate_series(11)
        first_model = fit_stage1_weighted_predictor(rows, TRAIN_LABEL_ROWS)
        second_model = fit_stage1_weighted_predictor(rows, TRAIN_LABEL_ROWS)

        self.assertEqual(first_model, second_model)

    def test_stage1_mean_metrics_clear_sprint1_baselines(self) -> None:
        maes = []
        rmses = []
        for seed in SEEDS:
            rows = generate_series(seed)
            model = fit_stage1_weighted_predictor(rows, TRAIN_LABEL_ROWS)
            labels = [float(rows[label_index]["target"]) for label_index in TEST_LABEL_ROWS]
            predictions = predict_stage1_weighted(rows, TEST_LABEL_ROWS, model)
            maes.append(mae(labels, predictions))
            rmses.append(rmse(labels, predictions))

        self.assertLess(sum(maes) / len(maes), 0.566021)
        self.assertLess(sum(rmses) / len(rmses), 0.703043)
        self.assertLess(sum(maes) / len(maes), 0.428163)
        self.assertLess(sum(rmses) / len(rmses), 0.540204)


if __name__ == "__main__":
    unittest.main()
