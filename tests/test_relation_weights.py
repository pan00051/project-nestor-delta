import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from nestor_delta.relation_weights import (  # noqa: E402
    compute_lagged_relation_weights,
    rank_target_sources,
)


class RelationWeightsTest(unittest.TestCase):
    def test_lagged_relation_weight_recovers_known_driver(self):
        rows = []
        for index in range(20):
            driver = float(index)
            noise = 1.0 if index % 2 == 0 else -1.0
            target = float(index - 1) if index > 0 else 0.0
            rows.append({"driver": driver, "noise": noise, "target": target})

        weights = compute_lagged_relation_weights(rows, ("driver", "noise", "target"), max_lag=3)
        ranked = rank_target_sources(weights, "target")

        self.assertEqual(ranked[0].source, "driver")
        self.assertEqual(ranked[0].lag, 1)
        self.assertGreater(ranked[0].score, ranked[1].score)

    def test_lagged_relation_weights_are_deterministic(self):
        rows = [
            {"a": 0.0, "b": 0.0},
            {"a": 1.0, "b": 0.0},
            {"a": 2.0, "b": 1.0},
            {"a": 3.0, "b": 2.0},
            {"a": 4.0, "b": 3.0},
        ]

        first = compute_lagged_relation_weights(rows, ("a", "b"), max_lag=2)
        second = compute_lagged_relation_weights(rows, ("a", "b"), max_lag=2)

        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
