from __future__ import annotations

import sys
import unittest
from dataclasses import replace
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from nestor_delta.baselines import (  # noqa: E402
    fit_linear_regression,
    predict_linear_regression,
)
from nestor_delta.config import (  # noqa: E402
    FEATURE_COLUMNS,
    LAG_WINDOW,
    SEEDS,
    TEST_LABEL_ROWS,
    TRAIN_LABEL_ROWS,
)
from nestor_delta.relation_weights import (  # noqa: E402
    RelationWeight,
    compute_lagged_relation_weights,
)
from nestor_delta.stage1_prediction import (  # noqa: E402
    build_stage1_features,
    fit_stage1_weighted_predictor,
)
from nestor_delta.synthetic import generate_series  # noqa: E402
from nestor_delta.trust_gated_prediction import (  # noqa: E402
    fit_trust_gated_predictor,
    predict_trust_gated,
)
from nestor_delta.trust_gating import build_trust_gates, linear_admission  # noqa: E402


class TrustGatingTests(unittest.TestCase):
    def test_piecewise_linear_admission_boundaries(self) -> None:
        self.assertEqual(linear_admission(0.10), 0.0)
        self.assertEqual(linear_admission(0.15), 0.0)
        self.assertAlmostEqual(linear_admission(0.325), 0.5)
        self.assertEqual(linear_admission(0.50), 1.0)
        self.assertEqual(linear_admission(0.90), 1.0)

    def test_noise_is_blocked_and_weak_driver_keeps_signed_admission(self) -> None:
        for seed in SEEDS:
            rows = generate_series(seed)
            train_history = rows[: max(TRAIN_LABEL_ROWS) + 1]
            weights = compute_lagged_relation_weights(
                train_history, FEATURE_COLUMNS, LAG_WINDOW
            )
            gates = {
                gate.source: gate for gate in build_trust_gates(weights, "target")
            }

            self.assertEqual(gates["noise"].admission, 0.0)
            self.assertEqual(gates["driver_b"].direction, -1.0)
            self.assertGreater(gates["driver_b"].admission, 0.0)
            self.assertLess(gates["driver_b"].admission, 1.0)
            self.assertEqual(gates["driver_a"].direction, 1.0)
            self.assertEqual(gates["driver_a"].admission, 1.0)

    def test_same_seed_gated_predictions_are_deterministic(self) -> None:
        rows = generate_series(11)
        first = fit_trust_gated_predictor(rows, TRAIN_LABEL_ROWS)
        second = fit_trust_gated_predictor(rows, TRAIN_LABEL_ROWS)

        self.assertEqual(first, second)
        self.assertEqual(
            predict_trust_gated(rows, TEST_LABEL_ROWS, first),
            predict_trust_gated(rows, TEST_LABEL_ROWS, second),
        )

    def test_trust_change_moves_gated_predictions(self) -> None:
        rows = generate_series(11)
        train_history = rows[: max(TRAIN_LABEL_ROWS) + 1]
        weights = compute_lagged_relation_weights(
            train_history, FEATURE_COLUMNS, LAG_WINDOW
        )
        stronger_weak_source = [
            _with_source_unit_trust(weight, "driver_b") for weight in weights
        ]

        default_model = fit_trust_gated_predictor(
            rows, TRAIN_LABEL_ROWS, relation_weights=weights
        )
        changed_model = fit_trust_gated_predictor(
            rows, TRAIN_LABEL_ROWS, relation_weights=stronger_weak_source
        )
        default_predictions = predict_trust_gated(
            rows, TEST_LABEL_ROWS, default_model
        )
        changed_predictions = predict_trust_gated(
            rows, TEST_LABEL_ROWS, changed_model
        )

        mean_delta = sum(
            abs(left - right)
            for left, right in zip(default_predictions, changed_predictions)
        ) / len(default_predictions)
        self.assertGreater(mean_delta, 0.01)

    def test_nonzero_scaling_change_does_not_move_sprint3_ols_predictions(self) -> None:
        rows = generate_series(11)
        stage1_model = fit_stage1_weighted_predictor(rows, TRAIN_LABEL_ROWS)
        unit_weights = tuple(
            _with_source_unit_trust(weight, "driver_b")
            for weight in stage1_model.selected_weights
        )

        original_train, train_labels = build_stage1_features(
            rows, TRAIN_LABEL_ROWS, stage1_model.selected_weights
        )
        changed_train, _ = build_stage1_features(
            rows, TRAIN_LABEL_ROWS, unit_weights
        )
        original_test, _ = build_stage1_features(
            rows, TEST_LABEL_ROWS, stage1_model.selected_weights
        )
        changed_test, _ = build_stage1_features(
            rows, TEST_LABEL_ROWS, unit_weights
        )
        original_predictions = predict_linear_regression(
            original_test, fit_linear_regression(original_train, train_labels)
        )
        changed_predictions = predict_linear_regression(
            changed_test, fit_linear_regression(changed_train, train_labels)
        )

        for original, changed in zip(original_predictions, changed_predictions):
            self.assertAlmostEqual(original, changed, places=10)


def _with_source_unit_trust(
    weight: RelationWeight, source: str
) -> RelationWeight:
    if weight.source != source or weight.target != "target":
        return weight
    direction = -1.0 if weight.weight < 0.0 else 1.0
    return replace(weight, weight=direction, score=1.0)


if __name__ == "__main__":
    unittest.main()
