from __future__ import annotations

import csv
import json
import math
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from nestor_delta.real_budget_sweep import (  # noqa: E402
    run_real_budget_sweep,
    write_real_budget_sweep_reports,
)
from nestor_delta.real_data import (  # noqa: E402
    RealCaseConfig,
    RealCaseData,
    load_real_case_config,
    load_real_case_data,
)
from nestor_delta.s5_config import BUDGET_RATIOS  # noqa: E402


FIXTURE_CONFIG = (
    REPO_ROOT / "data" / "real_budget_sweep_fixture" / "case.json"
)


class RealBudgetSweepTests(unittest.TestCase):
    def test_fixed_fixture_counts_and_proxies_are_monotonic(self) -> None:
        config, data, result = _load_fixture()

        self.assertEqual(
            [tier.budget_ratio for tier in result.tiers], list(BUDGET_RATIOS)
        )
        self.assertEqual(
            [round(tier.threshold, 2) for tier in result.tiers],
            [0.06, 0.17, 0.28, 0.39, 0.50],
        )
        self.assertEqual(
            [tier.candidate_count for tier in result.tiers], [15] * 5
        )
        self.assertEqual(
            [len(tier.retained_after_threshold) for tier in result.tiers],
            [15, 5, 4, 2, 0],
        )
        self.assertEqual(
            [len(tier.admitted_after_cap) for tier in result.tiers],
            [5, 5, 4, 2, 0],
        )
        self.assertEqual(
            [len(tier.selected_weights) for tier in result.tiers],
            [5, 5, 4, 2, 0],
        )
        self.assertTrue(
            _nonincreasing(
                [tier.profile.downstream_compute_proxy for tier in result.tiers]
            )
        )
        self.assertTrue(
            _nonincreasing(
                [tier.profile.downstream_memory_proxy for tier in result.tiers]
            )
        )
        self.assertEqual(
            result.tiers[-1].fit_status,
            "baseline_only_no_retained_signal",
        )
        self.assertEqual(config.max_selected_signals, 5)
        self.assertEqual(len(data.rows), 216)

    def test_future_test_values_do_not_change_any_frozen_tier(self) -> None:
        config, data, original = _load_fixture()
        changed_rows = []
        for date, row in zip(data.dates, data.rows):
            changed = dict(row)
            if date >= config.test_start:
                for offset, name in enumerate(sorted(changed), start=1):
                    changed[name] = float(changed[name]) + 1000.0 * offset
            changed_rows.append(changed)
        changed_data = RealCaseData(
            dates=data.dates,
            rows=tuple(changed_rows),
            variables=data.variables,
        )

        changed = run_real_budget_sweep(config, changed_data)

        self.assertEqual(_frozen_signature(original), _frozen_signature(changed))
        self.assertNotEqual(
            [tier.delta_mae for tier in original.tiers],
            [tier.delta_mae for tier in changed.tiers],
        )

    def test_physical_column_order_does_not_change_report_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first_config = _write_reordered_fixture(root / "first", reverse=False)
            second_config = _write_reordered_fixture(root / "second", reverse=True)

            first_paths = _run_and_write(first_config)
            second_paths = _run_and_write(second_config)

            for first, second in zip(first_paths, second_paths):
                self.assertEqual(first.read_bytes(), second.read_bytes(), first.name)

    def test_exact_and_near_collinearity_do_not_break_sweep(self) -> None:
        for mode in ("exact", "near"):
            with self.subTest(mode=mode):
                config, data = _collinear_case(mode)
                result = run_real_budget_sweep(config, data)

                self.assertEqual(len(result.tiers), 5)
                self.assertTrue(
                    all(
                        tier.fit_status
                        in {
                            "fit",
                            "fit_after_collinearity_backoff",
                            "baseline_only_no_stable_signal",
                            "baseline_only_no_retained_signal",
                        }
                        for tier in result.tiers
                    )
                )
                self.assertTrue(
                    all(
                        math.isfinite(coefficient)
                        for tier in result.tiers
                        for coefficient in tier.model_coefficients
                    )
                )
                if mode == "exact":
                    self.assertEqual(
                        result.tiers[0].fit_status,
                        "fit_after_collinearity_backoff",
                    )
                    self.assertIn(
                        "signal_b", result.tiers[0].dropped_collinear_sources
                    )

    def test_zero_signal_tiers_keep_delta_fields_empty(self) -> None:
        config, data = _zero_signal_case()
        result = run_real_budget_sweep(config, data)

        for tier in result.tiers:
            self.assertEqual(
                tier.fit_status, "baseline_only_no_retained_signal"
            )
            self.assertEqual(tier.selected_weights, ())
            self.assertEqual(tier.model_coefficients, ())
            self.assertIsNone(tier.delta_mae)
            self.assertIsNone(tier.delta_rmse)
            self.assertIsNone(tier.mae_change_vs_persistence_pct)
            self.assertEqual(tier.profile.downstream_compute_proxy, 0)
            self.assertEqual(tier.profile.downstream_memory_proxy, 0)
            self.assertTrue(all(value is None for value in tier.delta_predictions))

    def test_same_input_writes_byte_identical_reports(self) -> None:
        config, data, result = _load_fixture()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = write_real_budget_sweep_reports(
                root / "first", config, data, result
            )
            second = write_real_budget_sweep_reports(
                root / "second", config, data, result
            )

            for first_path, second_path in zip(first, second):
                self.assertEqual(
                    first_path.read_bytes(),
                    second_path.read_bytes(),
                    first_path.name,
                )


def _load_fixture():
    config = load_real_case_config(FIXTURE_CONFIG)
    data = load_real_case_data(config)
    return config, data, run_real_budget_sweep(config, data)


def _run_and_write(config_path: Path):
    config = load_real_case_config(config_path)
    data = load_real_case_data(config)
    result = run_real_budget_sweep(config, data)
    return write_real_budget_sweep_reports(config.output_dir, config, data, result)


def _write_reordered_fixture(root: Path, reverse: bool) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    source_config = json.loads(FIXTURE_CONFIG.read_text(encoding="utf-8"))
    source_csv = FIXTURE_CONFIG.parent / source_config["csv"]
    with source_csv.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))

    candidates = list(source_config["candidate_signals"])
    if reverse:
        candidates.reverse()
    fieldnames = ["date", "target"] + candidates
    csv_path = root / "data.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({name: row[name] for name in fieldnames})

    source_config.update(
        {
            "candidate_signals": candidates,
            "csv": "data.csv",
            "output_dir": "reports",
        }
    )
    config_path = root / "case.json"
    config_path.write_text(
        json.dumps(source_config, sort_keys=True) + "\n", encoding="utf-8"
    )
    return config_path


def _frozen_signature(result):
    return tuple(
        (
            tier.budget_ratio,
            tier.threshold,
            tier.candidate_count,
            tier.retained_after_threshold,
            tier.admitted_after_cap,
            tier.selected_weights,
            tier.dropped_collinear_sources,
            tier.model_coefficients,
            tier.fit_status,
            tier.profile,
        )
        for tier in result.tiers
    )


def _collinear_case(mode: str):
    dates = tuple(_month_label(index) for index in range(84))
    rows = []
    target = 0.0
    for index in range(84):
        signal_a = float((index * 7) % 29) * 100.0 + index * 13.0
        adjustment = 0.0 if mode == "exact" else float((index % 5) - 2) * 1e-5
        signal_b = 2.0 * signal_a + adjustment
        signal_c = float((index * 11) % 31) * 17.0
        target = (
            0.35 * target
            + 0.55 * signal_a
            + 0.08 * signal_c
            + float((index * index) % 7)
        )
        rows.append(
            {
                "target": target,
                "signal_a": signal_a,
                "signal_b": signal_b,
                "signal_c": signal_c,
            }
        )
    config = _memory_config(("signal_a", "signal_b", "signal_c"), 3)
    data = RealCaseData(
        dates=dates,
        rows=tuple(rows),
        variables=("target", "signal_a", "signal_b", "signal_c"),
    )
    return config, data


def _zero_signal_case():
    dates = tuple(_month_label(index) for index in range(84))
    rows = tuple(
        {
            "target": float((index * index + 3 * index) % 17),
            "constant_a": 1.0,
            "constant_b": 2.0,
        }
        for index in range(84)
    )
    config = _memory_config(("constant_a", "constant_b"), 2)
    data = RealCaseData(
        dates=dates,
        rows=rows,
        variables=("target", "constant_a", "constant_b"),
    )
    return config, data


def _memory_config(candidates, max_selected_signals: int) -> RealCaseConfig:
    return RealCaseConfig(
        case_name="memory_fixture",
        csv_path=Path("unused.csv"),
        date_column="date",
        target="target",
        candidate_signals=tuple(candidates),
        frequency="monthly",
        lag_window=2,
        train_end="2023-12",
        test_start="2024-01",
        max_selected_signals=max_selected_signals,
        output_dir=Path("unused_reports"),
        seasonal_period=0,
        notes="Test fixture only.",
    )


def _month_label(index: int) -> str:
    year = 2018 + index // 12
    month = index % 12 + 1
    return f"{year:04d}-{month:02d}"


def _nonincreasing(values) -> bool:
    return all(left >= right for left, right in zip(values, values[1:]))


if __name__ == "__main__":
    unittest.main()
