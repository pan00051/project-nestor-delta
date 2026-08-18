import math
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from nestor_delta.interval_metrics import (  # noqa: E402
    change_space_errors,
    sign_flip_null_interval,
    directional_accuracy,
    fold_skill,
    mase,
    skill_interval,
    worst_decile_error,
)
from nestor_delta.noise_floor import (  # noqa: E402
    correlation_noise_floor,
    fisher_z_threshold,
    lag_scan_noise_floor,
    sidak_alpha,
)
from nestor_delta.rolling_origin import (  # noqa: E402
    assert_folds_are_past_only,
    build_rolling_origin_folds,
)


class RollingOriginTest(unittest.TestCase):
    def test_folds_never_train_on_their_own_origin_or_later(self):
        folds = build_rolling_origin_folds(
            list(range(0, 60)), test_size=1, min_train_size=30
        )
        assert_folds_are_past_only(folds)
        for fold in folds:
            self.assertLess(max(fold.train_label_rows), fold.origin)

    def test_expanding_window_grows_and_sliding_window_does_not(self):
        expanding = build_rolling_origin_folds(
            list(range(0, 50)), test_size=1, min_train_size=20, expanding=True
        )
        sliding = build_rolling_origin_folds(
            list(range(0, 50)), test_size=1, min_train_size=20, expanding=False
        )
        self.assertGreater(
            len(expanding[-1].train_label_rows), len(expanding[0].train_label_rows)
        )
        self.assertEqual(
            {len(fold.train_label_rows) for fold in sliding}, {20}
        )

    def test_fold_construction_is_deterministic(self):
        first = build_rolling_origin_folds(list(range(0, 40)), 2, 15)
        second = build_rolling_origin_folds(list(range(0, 40)), 2, 15)
        self.assertEqual(first, second)

    def test_single_split_is_the_one_fold_special_case(self):
        folds = build_rolling_origin_folds(
            list(range(0, 40)), test_size=10, min_train_size=30, max_folds=1
        )
        self.assertEqual(len(folds), 1)
        self.assertEqual(len(folds[0].test_label_rows), 10)

    def test_unsorted_or_duplicate_label_rows_are_rejected(self):
        with self.assertRaises(ValueError):
            build_rolling_origin_folds([3, 1, 2], test_size=1, min_train_size=1)
        with self.assertRaises(ValueError):
            build_rolling_origin_folds([1, 1, 2], test_size=1, min_train_size=1)

    def test_insufficient_history_fails_explicitly(self):
        with self.assertRaises(ValueError):
            build_rolling_origin_folds(list(range(5)), test_size=3, min_train_size=4)


class NoiseFloorTest(unittest.TestCase):
    def test_threshold_falls_as_sample_count_rises(self):
        self.assertGreater(fisher_z_threshold(30), fisher_z_threshold(300))

    def test_lag_scan_threshold_exceeds_single_comparison_threshold(self):
        single = correlation_noise_floor(191, comparisons=1).threshold
        scanned = lag_scan_noise_floor(191, max_lag=6).threshold
        self.assertGreater(scanned, single)

    def test_frozen_sprint5_constant_sits_below_the_noise_floor(self):
        # BENCHMARK_NOISE_FLOOR is 0.06 and does not depend on n. At the Spain
        # train window size it admits correlations indistinguishable from luck.
        floor = correlation_noise_floor(191, comparisons=1)
        self.assertGreater(floor.threshold, 0.06)
        self.assertFalse(floor.clears(0.06))

    def test_sidak_alpha_is_stricter_for_more_comparisons(self):
        self.assertLess(sidak_alpha(0.05, 6), sidak_alpha(0.05, 1))
        self.assertAlmostEqual(sidak_alpha(0.05, 1), 0.05, places=12)

    def test_invalid_arguments_fail_explicitly(self):
        with self.assertRaises(ValueError):
            fisher_z_threshold(3)
        with self.assertRaises(ValueError):
            correlation_noise_floor(100, comparisons=0)
        with self.assertRaises(ValueError):
            fisher_z_threshold(100, alpha=0.0)


class IntervalMetricsTest(unittest.TestCase):
    def test_perfect_forecast_scores_zero_on_every_metric(self):
        actual = [1.0, 2.0, 3.0, 4.0]
        self.assertEqual(worst_decile_error(actual, actual), 0.0)
        self.assertEqual(mase(actual, actual, [1.0, 2.0, 3.0]), 0.0)

    def test_mase_is_invariant_to_the_level_of_the_series(self):
        actual = [10.0, 11.0, 12.0]
        predicted = [10.5, 11.5, 12.5]
        train = [7.0, 8.0, 9.0]
        shift = 1000.0
        self.assertAlmostEqual(
            mase(actual, predicted, train),
            mase(
                [v + shift for v in actual],
                [v + shift for v in predicted],
                [v + shift for v in train],
            ),
            places=12,
        )

    def test_persistence_never_decides_a_direction(self):
        previous = [1.0, 2.0, 3.0]
        actual = [2.0, 3.0, 4.0]
        result = directional_accuracy(actual, previous, previous)
        self.assertEqual(result["decided"], 0.0)
        self.assertTrue(math.isnan(result["accuracy"]))

    def test_directional_accuracy_counts_only_decided_forecasts(self):
        previous = [1.0, 1.0, 1.0, 1.0]
        actual = [2.0, 0.0, 2.0, 0.0]
        predicted = [1.5, 1.5, 0.5, 1.0]  # up, up, down, flat
        # actual moves are up, down, up, down -> only the first call is right.
        result = directional_accuracy(actual, predicted, previous)
        self.assertAlmostEqual(result["decided"], 0.75)
        self.assertAlmostEqual(result["accuracy"], 1.0 / 3.0)

    def test_worst_decile_error_reports_the_tail_not_the_average(self):
        actual = [0.0] * 20
        predicted = [0.0] * 19 + [100.0]
        self.assertGreater(
            worst_decile_error(actual, predicted),
            sum(abs(a - p) for a, p in zip(actual, predicted)) / len(actual),
        )

    def test_change_space_exposes_error_hidden_by_the_level(self):
        previous = [100.0, 100.0, 100.0]
        actual = [100.5, 100.5, 100.5]
        predicted = [100.0, 100.0, 100.0]  # persistence: zero change forecast
        result = change_space_errors(actual, predicted, previous)
        # 0.5 of error on a level near 100 is 0.5%, but it is 100% of the move.
        self.assertAlmostEqual(result["error_share_of_move"], 1.0)

    def test_identical_model_and_baseline_score_zero_skill(self):
        self.assertEqual(fold_skill(1.25, 1.25), 0.0)

    def test_interval_is_reproducible_and_brackets_the_median(self):
        values = [0.02, -0.01, 0.05, 0.00, -0.03, 0.04, 0.01]
        first = skill_interval(values)
        second = skill_interval(values)
        self.assertEqual(first, second)
        self.assertLessEqual(first.low, first.median)
        self.assertLessEqual(first.median, first.high)

    def test_noisy_zero_effect_interval_contains_zero(self):
        # A model with no real advantage must not be reported as a winner.
        values = [0.04, -0.05, 0.03, -0.02, 0.01, -0.04, 0.02, -0.01]
        self.assertFalse(skill_interval(values).excludes_zero)

    def test_consistent_advantage_interval_excludes_zero(self):
        values = [0.20, 0.22, 0.19, 0.25, 0.21, 0.23, 0.24, 0.20]
        self.assertTrue(skill_interval(values).excludes_zero)

    def test_empty_input_fails_explicitly(self):
        with self.assertRaises(ValueError):
            skill_interval([])
        with self.assertRaises(ValueError):
            worst_decile_error([], [])


class SignFlipNullTest(unittest.TestCase):
    def test_null_is_centred_on_zero_and_contains_it(self):
        skills = [0.4, -0.1, 0.9, -0.6, 0.2, 0.05, -0.3, 0.7, -0.2, 0.5]
        null = sign_flip_null_interval(skills)
        self.assertEqual(null.median, 0.0)
        self.assertLessEqual(null.low, 0.0)
        self.assertGreaterEqual(null.high, 0.0)

    def test_null_band_is_roughly_symmetric_about_zero(self):
        skills = [0.4, -0.1, 0.9, -0.6, 0.2, 0.05, -0.3, 0.7, -0.2, 0.5]
        null = sign_flip_null_interval(skills)
        self.assertAlmostEqual(abs(null.low), abs(null.high), delta=0.2 * abs(null.high))

    def test_null_does_not_collapse_to_a_point(self):
        # A skewed sample with one dominant fold must still yield a spread,
        # not a degenerate low==high band (the LCG low-bit regression).
        skills = [5.0, -0.1, 0.2, -0.05, 0.1, -0.2, 0.15, -0.1, 0.05, -0.05]
        null = sign_flip_null_interval(skills)
        self.assertLess(null.low, null.high)
        self.assertLessEqual(null.low, 0.0)
        self.assertGreaterEqual(null.high, 0.0)

    def test_null_is_reproducible(self):
        skills = [0.3, -0.2, 0.5, -0.4, 0.1]
        self.assertEqual(sign_flip_null_interval(skills), sign_flip_null_interval(skills))


if __name__ == "__main__":
    unittest.main()
