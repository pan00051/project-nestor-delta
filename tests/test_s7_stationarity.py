import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from nestor_delta.relation_weights import (  # noqa: E402
    compute_lagged_relation_weights,
    legacy_level_scoring,
)
from nestor_delta.s7_fixtures import (  # noqa: E402
    fixture_a_summaries,
    fixture_b_summaries,
)
from nestor_delta.stationarity import (  # noqa: E402
    compute_transformed_relation_weights,
    signal_diagnostics,
    validate_transform_declarations,
)


class S7StationarityTests(unittest.TestCase):
    def test_legacy_level_scoring_matches_frozen_function(self) -> None:
        rows = [
            {"x": 0.0, "y": 0.0},
            {"x": 1.0, "y": 0.0},
            {"x": 2.0, "y": 1.0},
            {"x": 3.0, "y": 2.0},
        ]

        self.assertEqual(
            legacy_level_scoring(rows, ("x", "y"), 2),
            compute_lagged_relation_weights(rows, ("x", "y"), 2),
        )
        self.assertEqual(
            legacy_level_scoring(rows, ("x", "y"), 2)[0].transform,
            "none",
        )

    def test_transform_declarations_are_explicit_and_validated(self) -> None:
        self.assertEqual(
            validate_transform_declarations(
                ("x", "y"), {"x": "diff", "y": "log_diff"}
            ),
            {"x": "diff", "y": "log_diff"},
        )
        with self.assertRaisesRegex(ValueError, "missing transform declarations"):
            validate_transform_declarations(("x", "y"), {"x": "diff"})
        with self.assertRaisesRegex(ValueError, "none/diff/log_diff"):
            validate_transform_declarations(("x",), {"x": "auto"})

    def test_high_acf_level_scoring_is_refused_in_s7_path(self) -> None:
        rows = [{"x": float(index), "y": float(index)} for index in range(40)]

        diagnostics = signal_diagnostics(rows, ("x", "y"), {"x": "diff", "y": "diff"})

        self.assertTrue(all(item.highly_persistent_risk for item in diagnostics))
        with self.assertRaisesRegex(ValueError, "refuses level scoring"):
            compute_transformed_relation_weights(
                rows, ("x", "y"), 2, {"x": "none", "y": "none"}
            )

    def test_fixture_a_kills_independent_random_walk_pseudo_relation(self) -> None:
        legacy, transformed = fixture_a_summaries(max_lag=3)

        self.assertGreaterEqual(legacy.median_abs_r, 0.35)
        self.assertGreaterEqual(legacy.pass_rate_gt_006, 0.90)
        self.assertLessEqual(transformed.median_abs_r, 0.10)
        self.assertEqual(transformed.pass_rate_gt_030, 0.0)

    def test_fixture_b_recovers_true_short_run_lag(self) -> None:
        _, transformed = fixture_b_summaries(max_lag=3)

        self.assertEqual(transformed.correct_lag_rate, 1.0)
        self.assertGreater(transformed.median_abs_r, 0.30)


if __name__ == "__main__":
    unittest.main()
