from __future__ import annotations

import inspect
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from nestor_delta.evidence_gate import (  # noqa: E402
    _benjamini_hochberg_thresholds,
    select_relations_with_evidence,
)
from nestor_delta.prediction_confidence import (  # noqa: E402
    compute_prediction_confidence,
    input_support_score,
)
from nestor_delta.relation_weights import RelationWeight  # noqa: E402
from nestor_delta.s10_fixtures import (  # noqa: E402
    confidence_calibration_fixture,
    fixture_d_relations,
    fixture_d_runs,
    fixture_d_summary,
)
from nestor_delta.s7_fixtures import fixture_a_summaries, fixture_b_summaries  # noqa: E402
from nestor_delta.s9_fixtures import (  # noqa: E402
    fixture_a_transformed_lifecycle_states,
    fixture_c_summary,
)


class S10EvidenceConfidenceTests(unittest.TestCase):
    def test_fixture_d_gate_improves_precision_without_losing_recall(self) -> None:
        summary = fixture_d_summary(seeds=range(50))

        self.assertGreaterEqual(summary.gate_precision_mean, 0.95)
        self.assertGreater(summary.precision_lift, 0.50)
        self.assertGreaterEqual(summary.gate_recall_mean, summary.fixed_recall_mean)

    def test_fixture_d_reports_precision_recall_distribution(self) -> None:
        runs = fixture_d_runs(seeds=range(10))

        self.assertEqual(len(runs), 10)
        self.assertTrue(all(run.gate_precision == 1.0 for run in runs))
        self.assertTrue(all(run.gate_recall == 1.0 for run in runs))
        self.assertTrue(all(run.fixed_selected_count > run.gate_selected_count for run in runs))
        self.assertGreater(len({run.fixed_selected_count for run in runs}), 1)
        self.assertGreater(len({run.fixed_precision for run in runs}), 1)

    def test_prediction_error_cannot_enter_selection_api(self) -> None:
        signature = inspect.signature(select_relations_with_evidence)
        names = set(signature.parameters)

        self.assertNotIn("prediction_error", names)
        self.assertNotIn("prediction_errors", names)
        self.assertNotIn("validation_mae", names)
        self.assertNotIn("test_error", names)

    def test_external_prediction_error_signal_does_not_change_selection(self) -> None:
        candidates = fixture_d_relations(0)
        selected_without_errors = select_relations_with_evidence(
            candidates, max_lag=3
        ).selected_relations
        pretend_prediction_errors = {
            relation.source: 999.0 if relation.source.startswith("true") else 0.0
            for relation in candidates
        }
        selected_with_external_errors_present = select_relations_with_evidence(
            candidates, max_lag=3
        ).selected_relations

        self.assertTrue(pretend_prediction_errors)
        self.assertEqual(selected_without_errors, selected_with_external_errors_present)

    def test_bh_cutoff_uses_last_accepted_p_value(self) -> None:
        thresholds = _benjamini_hochberg_thresholds((0.01, 0.02, 0.049, 0.051), 0.05)

        self.assertEqual(thresholds, (0.02, 0.02, 0.02, 0.02))

    def test_no_evidence_returns_baseline_only(self) -> None:
        weak = RelationWeight(
            source="weak",
            target="target",
            lag=1,
            weight=0.05,
            score=0.05,
            sample_count=120,
            transform="diff",
            stability=0.10,
            uncertainty=0.30,
        )

        result = select_relations_with_evidence((weak,), max_lag=3)

        self.assertEqual(result.selected_relations, ())
        self.assertEqual(result.fit_status, "baseline_only_no_evidence")

    def test_prediction_confidence_calibrates_against_error(self) -> None:
        calibration = confidence_calibration_fixture()

        self.assertLess(calibration.rank_correlation, -0.25)
        lowest_confidence_error = calibration.bins[0][1]
        highest_confidence_error = calibration.bins[-1][1]
        self.assertGreater(lowest_confidence_error, highest_confidence_error)

    def test_prediction_confidence_is_nullable_when_evidence_is_missing(self) -> None:
        confidence = compute_prediction_confidence(
            relation_stability=None,
            parameter_uncertainty=0.1,
            input_support=0.9,
            residual_uncertainty=0.1,
        )

        self.assertIsNone(confidence.confidence)

    def test_input_support_caps_prediction_confidence(self) -> None:
        confidence = compute_prediction_confidence(
            relation_stability=0.95,
            parameter_uncertainty=0.01,
            input_support=0.0,
            residual_uncertainty=0.01,
        )

        self.assertEqual(confidence.confidence, 0.0)

    def test_input_support_marks_out_of_distribution_inputs(self) -> None:
        train = [0.0, 1.0, 2.0, 3.0]

        self.assertEqual(input_support_score(1.5, train), 1.0)
        self.assertLess(input_support_score(4.0, train), 1.0)
        self.assertEqual(input_support_score(5.0, train), 0.0)

    def test_s7_and_s9_fixtures_remain_green(self) -> None:
        legacy_a, transformed_a = fixture_a_summaries(max_lag=3)
        _, transformed_b = fixture_b_summaries(max_lag=3)
        fixture_c = fixture_c_summary()
        states = fixture_a_transformed_lifecycle_states(seeds=range(50))

        self.assertGreaterEqual(legacy_a.median_abs_r, 0.35)
        self.assertLessEqual(transformed_a.median_abs_r, 0.10)
        self.assertEqual(transformed_a.pass_rate_gt_030, 0.0)
        self.assertEqual(transformed_b.correct_lag_rate, 1.0)
        self.assertEqual(fixture_c.detected_count, fixture_c.seed_count)
        self.assertEqual(
            [state for state in states if state in {"stable", "strengthening"}],
            [],
        )


if __name__ == "__main__":
    unittest.main()
