from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from nestor_delta.config import FEATURE_COLUMNS, LAG_WINDOW, TEST_LABEL_ROWS  # noqa: E402
from nestor_delta.resource_adaptive_ignore import (  # noqa: E402
    downstream_profile,
    threshold_for_budget,
)
from nestor_delta.resource_adaptive_prediction import (  # noqa: E402
    fit_adaptive_ignore_predictor,
    predict_adaptive_ignore,
)
from nestor_delta.s4_config import DYNAMIC_TRAIN_LABEL_ROWS  # noqa: E402
from nestor_delta.s5_config import (  # noqa: E402
    BUDGET_RATIOS,
    RESOURCE_STRESS_COLUMNS,
    RESOURCE_STRESS_LAG_WINDOW,
    RESOURCE_STRESS_TEST_LABEL_ROWS,
    RESOURCE_STRESS_TRAIN_LABEL_ROWS,
)
from nestor_delta.synthetic_drift import generate_drift_series  # noqa: E402
from nestor_delta.synthetic_resource_stress import (  # noqa: E402
    generate_resource_stress_series,
    write_resource_stress_csv,
)


class ResourceAdaptiveIgnoreTests(unittest.TestCase):
    def test_budget_threshold_schedule_is_frozen(self) -> None:
        expected = {
            1.00: 0.06,
            0.75: 0.17,
            0.50: 0.28,
            0.25: 0.39,
            0.00: 0.50,
        }
        for budget_ratio, threshold in expected.items():
            self.assertAlmostEqual(
                threshold_for_budget(budget_ratio), threshold, places=10
            )

    def test_downstream_profile_uses_retained_relations(self) -> None:
        profile = downstream_profile(
            budget_ratio=0.50,
            retained_relation_count=7,
            downstream_lag_count=5,
            materialized_lag_count=5,
            effective_row_count=415,
        )

        self.assertEqual(profile.downstream_compute_proxy, 7 * 5 * 415)
        self.assertEqual(profile.downstream_memory_proxy, 7 * 5 * 415)
        self.assertEqual(profile.estimated_memory_bytes, 7 * 5 * 415 * 8)

    def test_s4_regression_keeps_known_drivers_and_blocks_noise_under_pressure(self) -> None:
        rows = generate_drift_series(101)
        model = fit_adaptive_ignore_predictor(
            rows,
            DYNAMIC_TRAIN_LABEL_ROWS,
            variables=FEATURE_COLUMNS,
            budget_ratio=0.75,
            lag_window=LAG_WINDOW,
        )

        sources = {relation.source for relation in model.retained_relations}
        self.assertEqual(sources, {"driver_a", "driver_b"})

    def test_lower_budget_monotonically_reduces_resource_stress_relations(self) -> None:
        rows = generate_resource_stress_series(211)
        models = [
            fit_adaptive_ignore_predictor(
                rows,
                RESOURCE_STRESS_TRAIN_LABEL_ROWS,
                variables=RESOURCE_STRESS_COLUMNS,
                budget_ratio=budget_ratio,
                lag_window=RESOURCE_STRESS_LAG_WINDOW,
            )
            for budget_ratio in BUDGET_RATIOS
        ]
        counts = [len(model.retained_relations) for model in models]
        compute = [model.profile.downstream_compute_proxy for model in models]
        memory = [model.profile.downstream_memory_proxy for model in models]

        self.assertEqual(counts, sorted(counts, reverse=True))
        self.assertEqual(compute, sorted(compute, reverse=True))
        self.assertEqual(memory, sorted(memory, reverse=True))
        self.assertLess(counts[-1], counts[0])

    def test_weak_relations_drop_before_strong_relations_on_stress_fixture(self) -> None:
        rows = generate_resource_stress_series(211)
        model = fit_adaptive_ignore_predictor(
            rows,
            RESOURCE_STRESS_TRAIN_LABEL_ROWS,
            variables=RESOURCE_STRESS_COLUMNS,
            budget_ratio=0.50,
            lag_window=RESOURCE_STRESS_LAG_WINDOW,
        )
        sources = {relation.source for relation in model.retained_relations}

        self.assertTrue({"strong_1", "strong_2", "strong_3"}.issubset(sources))
        self.assertFalse(any(source.startswith("weak_") for source in sources))
        self.assertFalse(any(source.startswith("noise_") for source in sources))

    def test_threshold_decision_excludes_current_and_future_rows(self) -> None:
        rows = generate_resource_stress_series(211)
        changed = [dict(row) for row in rows]
        changed[510]["target"] += 1000.0
        changed[599]["target"] -= 1000.0

        original = fit_adaptive_ignore_predictor(
            rows,
            RESOURCE_STRESS_TRAIN_LABEL_ROWS,
            variables=RESOURCE_STRESS_COLUMNS,
            budget_ratio=0.50,
            lag_window=RESOURCE_STRESS_LAG_WINDOW,
        )
        after_change = fit_adaptive_ignore_predictor(
            changed,
            RESOURCE_STRESS_TRAIN_LABEL_ROWS,
            variables=RESOURCE_STRESS_COLUMNS,
            budget_ratio=0.50,
            lag_window=RESOURCE_STRESS_LAG_WINDOW,
        )

        self.assertEqual(original.retained_relations, after_change.retained_relations)
        self.assertEqual(original.coefficients, after_change.coefficients)
        self.assertEqual(
            predict_adaptive_ignore(
                rows, (510,), original, lag_window=RESOURCE_STRESS_LAG_WINDOW
            ),
            predict_adaptive_ignore(
                changed, (510,), after_change, lag_window=RESOURCE_STRESS_LAG_WINDOW
            ),
        )

    def test_resource_stress_csv_is_byte_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = root / "first.csv"
            second = root / "second.csv"

            write_resource_stress_csv(generate_resource_stress_series(211), first)
            write_resource_stress_csv(generate_resource_stress_series(211), second)

            self.assertEqual(first.read_bytes(), second.read_bytes())


if __name__ == "__main__":
    unittest.main()
