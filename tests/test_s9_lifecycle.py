from __future__ import annotations

import sys
import unittest
from pathlib import Path
from statistics import median

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from nestor_delta.dynamic_weights import (  # noqa: E402
    TimedRelationWeight,
    compute_rolling_transformed_relation_weights,
    target_source_trajectory,
)
from nestor_delta.relation_weights import RelationWeight  # noqa: E402
from nestor_delta.s9_fixtures import (  # noqa: E402
    FIXTURE_C_K,
    fixture_a_transformed_lifecycle_states,
    fixture_a_transformed_stability_scores,
    fixture_c_detection_lags,
    relation_death_rows,
)
from nestor_delta.temporal_stability import (  # noqa: E402
    aggregate_relation_trajectory,
    classify_relation_lifecycle,
)


class S9LifecycleTests(unittest.TestCase):
    def test_relation_object_v1_adds_only_s9_nullable_fields(self) -> None:
        relation = RelationWeight("x", "y", 1, 0.5, 0.5, 30, transform="diff")

        self.assertIsNone(relation.stability)
        self.assertIsNone(relation.uncertainty)
        self.assertIsNone(relation.selected)
        self.assertFalse(hasattr(relation, "direction"))

    def test_insufficient_evidence_keeps_s9_fields_null(self) -> None:
        trajectory = (
            TimedRelationWeight(10, 0, 10, "x", "y", 1, 0.4, 0.4, 9, "diff"),
            TimedRelationWeight(11, 1, 11, "x", "y", 1, 0.5, 0.5, 9, "diff"),
        )

        relation = aggregate_relation_trajectory(trajectory, min_points=6)
        lifecycle = classify_relation_lifecycle(trajectory, min_points=6)

        self.assertIsNone(relation.stability)
        self.assertIsNone(relation.uncertainty)
        self.assertIsNone(relation.selected)
        self.assertEqual(lifecycle.state, "birth")

    def test_fixture_c_detects_relation_death_within_k_steps(self) -> None:
        lags = fixture_c_detection_lags(seeds=range(30))

        self.assertTrue(all(lag is not None for lag in lags))
        self.assertLessEqual(max(lag for lag in lags if lag is not None), FIXTURE_C_K)
        self.assertLessEqual(median(lag for lag in lags if lag is not None), 18)

    def test_fixture_a_transformed_pseudo_relation_is_not_backed_by_stability(
        self,
    ) -> None:
        stability_scores = fixture_a_transformed_stability_scores(seeds=range(30))

        self.assertGreater(len(stability_scores), 0)
        self.assertLessEqual(median(stability_scores), 0.15)
        self.assertLessEqual(max(stability_scores), 0.45)

        # The decisive guard: no pure-noise trajectory may be endorsed as a
        # live relationship. Checking the stability score alone is not enough;
        # the lifecycle STATE is what downstream consumes.
        states = fixture_a_transformed_lifecycle_states(seeds=range(50))
        endorsed = [state for state in states if state in {"stable", "strengthening"}]
        self.assertEqual(endorsed, [], f"noise endorsed as live relations: {endorsed}")

    def test_old_history_does_not_keep_dead_relation_stable(self) -> None:
        rows = relation_death_rows(7, n=260, death_step=180)
        weights = compute_rolling_transformed_relation_weights(
            rows,
            ("x", "y"),
            3,
            range(40, 241),
            36,
            {"x": "diff", "y": "diff"},
        )
        trajectory = tuple(
            weight
            for weight in target_source_trajectory(weights, "y", "x")
            if weight.step <= 240
        )

        lifecycle = classify_relation_lifecycle(trajectory)

        self.assertIn(lifecycle.state, {"decaying", "dead"})
        self.assertIsNotNone(lifecycle.relation.stability)
        self.assertLess(lifecycle.relation.stability, 0.25)
        self.assertGreater(lifecycle.relation.sample_count, 25)


if __name__ == "__main__":
    unittest.main()
