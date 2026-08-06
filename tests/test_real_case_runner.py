from __future__ import annotations

import csv
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from nestor_delta.real_case_analysis import run_real_case_analysis  # noqa: E402
from nestor_delta.real_data import (  # noqa: E402
    load_real_case_config,
    load_real_case_data,
)


class RealCaseRunnerTests(unittest.TestCase):
    def test_runner_writes_expected_reports(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config_path = _write_case(root, ("signal_a", "signal_b", "noise"))

            subprocess.run(
                [sys.executable, str(REPO_ROOT / "scripts" / "run_real_case.py"), str(config_path)],
                check=True,
                cwd=REPO_ROOT,
            )

            reports = root / "reports"
            self.assertTrue((reports / "relation_ranking.csv").exists())
            self.assertTrue((reports / "prediction_metrics.csv").exists())
            self.assertTrue((reports / "predictions_vs_actual.csv").exists())
            self.assertTrue((reports / "resource_tradeoff.csv").exists())
            self.assertTrue((reports / "summary.md").exists())

    def test_candidate_column_order_does_not_change_csv_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first_root = root / "first"
            second_root = root / "second"
            _run_script(_write_case(first_root, ("signal_a", "signal_b", "noise")))
            _run_script(_write_case(second_root, ("noise", "signal_b", "signal_a")))

            for filename in (
                "relation_ranking.csv",
                "prediction_metrics.csv",
                "predictions_vs_actual.csv",
                "resource_tradeoff.csv",
            ):
                self.assertEqual(
                    (first_root / "reports" / filename).read_bytes(),
                    (second_root / "reports" / filename).read_bytes(),
                    filename,
                )

    def test_future_test_values_do_not_change_train_selection_or_coefficients(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            original_path = _write_case(root / "original", ("signal_a", "signal_b", "noise"))
            changed_path = _write_case(
                root / "changed",
                ("signal_a", "signal_b", "noise"),
                corrupt_test=True,
            )

            original = _load_and_run(original_path)
            changed = _load_and_run(changed_path)

            self.assertEqual(original.ranking, changed.ranking)
            self.assertEqual(original.selected_weights, changed.selected_weights)
            self.assertEqual(_fit_signature(original_path), _fit_signature(changed_path))
            self.assertEqual(original.fit_status, changed.fit_status)

    def test_partial_collinearity_removes_redundant_lower_rank_signal(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            result = _run_case(
                Path(directory),
                ("signal_a", "signal_b", "signal_c"),
                mode="partial_collinear",
                max_selected_signals=3,
            )

            self.assertEqual(result.fit_status, "fit_after_collinearity_backoff")
            self.assertIn("signal_b", result.dropped_collinear_sources)
            self.assertIn("signal_a", [weight.source for weight in result.selected_weights])
            self.assertIn("signal_c", [weight.source for weight in result.selected_weights])

    def test_complete_collinearity_drops_to_one_stable_signal(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            result = _run_case(
                Path(directory),
                ("signal_a", "signal_b", "signal_c"),
                mode="complete_collinear",
                max_selected_signals=3,
            )

            self.assertEqual(result.fit_status, "fit_after_collinearity_backoff")
            self.assertEqual(len(result.selected_weights), 1)
            self.assertEqual(len(result.dropped_collinear_sources), 2)

    def test_no_stable_signal_keeps_baseline_only(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            result = _run_case(
                Path(directory),
                ("signal_a", "signal_b"),
                mode="no_stable_signal",
                max_selected_signals=2,
            )

            self.assertEqual(result.fit_status, "baseline_only_no_stable_signal")
            self.assertEqual(result.selected_weights, ())
            self.assertEqual([row["method"] for row in result.metric_rows], ["persistence"])

    def test_bad_config_fails_clearly(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            duplicate = _write_case(root / "duplicate", ("signal_a", "signal_a", "noise"))
            with self.assertRaisesRegex(ValueError, "candidate_signals must be unique"):
                load_real_case_config(duplicate)

            missing = _write_case(root / "missing", ("signal_a", "signal_b", "noise"))
            payload = json.loads(missing.read_text(encoding="utf-8"))
            del payload["frequency"]
            missing.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "missing required fields"):
                load_real_case_config(missing)

            extra = _write_case(root / "extra", ("signal_a", "signal_b", "noise"))
            payload = json.loads(extra.read_text(encoding="utf-8"))
            payload["unexpected"] = True
            extra.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "unknown fields"):
                load_real_case_config(extra)

            bad_type = _write_case(root / "bad_type", ("signal_a", "signal_b", "noise"))
            payload = json.loads(bad_type.read_text(encoding="utf-8"))
            payload["lag_window"] = "2"
            bad_type.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "must be an integer"):
                load_real_case_config(bad_type)

    def test_dirty_csv_fails_without_guessing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            missing_value = _write_case(root / "missing_value", ("signal_a", "signal_b", "noise"))
            _replace_csv_value(root / "missing_value" / "data.csv", row_index=5, column="signal_a", value="")
            with self.assertRaisesRegex(ValueError, "non-numeric value"):
                _load_data_only(missing_value)

            bad_date = _write_case(root / "bad_date", ("signal_a", "signal_b", "noise"))
            _replace_csv_value(root / "bad_date" / "data.csv", row_index=5, column="date", value="2020/05")
            with self.assertRaisesRegex(ValueError, "YYYY-MM"):
                _load_data_only(bad_date)

            gap = _write_case(root / "gap", ("signal_a", "signal_b", "noise"))
            _delete_csv_row(root / "gap" / "data.csv", row_index=5)
            with self.assertRaisesRegex(ValueError, "monthly without gaps"):
                _load_data_only(gap)


def _run_script(config_path: Path) -> None:
    subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "run_real_case.py"), str(config_path)],
        check=True,
        cwd=REPO_ROOT,
        stdout=subprocess.DEVNULL,
    )


def _run_case(root: Path, candidate_order, mode: str = "normal", max_selected_signals: int = 2):
    return _load_and_run(_write_case(root, candidate_order, mode=mode, max_selected_signals=max_selected_signals))


def _load_and_run(config_path: Path):
    config = load_real_case_config(config_path)
    data = load_real_case_data(config)
    return run_real_case_analysis(config, data)


def _load_data_only(config_path: Path):
    config = load_real_case_config(config_path)
    return load_real_case_data(config)


def _write_case(
    root: Path,
    candidate_order,
    mode: str = "normal",
    corrupt_test: bool = False,
    max_selected_signals: int = 2,
) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    csv_path = root / "data.csv"
    config_path = root / "case.json"
    fieldnames = ("date", "target") + tuple(candidate_order)
    rows = _fixture_rows(mode, corrupt_test)

    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row[key] for key in fieldnames})

    config_path.write_text(
        json.dumps(
            {
                "case_name": "fixture_case",
                "csv": "data.csv",
                "date_column": "date",
                "target": "target",
                "candidate_signals": list(candidate_order),
                "frequency": "monthly",
                "lag_window": 2,
                "train_end": "2021-12",
                "test_start": "2022-02",
                "max_selected_signals": max_selected_signals,
                "seasonal_period": 0,
                "output_dir": "reports",
                "notes": "Test fixture only.",
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return config_path


def _fixture_rows(mode: str, corrupt_test: bool):
    rows = []
    target = 0.0
    for index in range(40):
        signal_a = float((index * 5) % 23) + index * 0.13
        if mode in {"partial_collinear", "complete_collinear", "no_stable_signal"}:
            signal_b = signal_a * 2.0
        else:
            signal_b = float((index * index) % 37)
        signal_c = signal_a * 3.0 if mode in {"complete_collinear", "no_stable_signal"} else float((index * 11) % 31)
        noise = float((index * 7) % 5)
        nonlinear = float((index * index) % 7)
        target = 0.4 * target + 0.8 * signal_a - 0.3 * signal_b + signal_c * 0.02 + noise * 0.01
        if mode == "complete_collinear":
            target += nonlinear
        row = {
            "date": _month_label(index),
            "target": target,
            "signal_a": signal_a,
            "signal_b": signal_b,
            "signal_c": signal_c,
            "noise": noise,
        }
        if mode == "no_stable_signal":
            row["target"] = signal_a * 5.0
        if corrupt_test and index >= 25:
            for key in ("target", "signal_a", "signal_b", "signal_c", "noise"):
                row[key] = float(row[key]) + 1000.0
        rows.append({key: (value if key == "date" else f"{float(value):.10f}") for key, value in row.items()})
    return rows


def _month_label(index: int) -> str:
    year = 2020 + index // 12
    month = index % 12 + 1
    return f"{year}-{month:02d}"


def _replace_csv_value(path: Path, row_index: int, column: str, value: str) -> None:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
        fieldnames = list(rows[0].keys())
    rows[row_index][column] = value
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _delete_csv_row(path: Path, row_index: int) -> None:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
        fieldnames = list(rows[0].keys())
    del rows[row_index]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _fit_signature(config_path: Path):
    result = _load_and_run(config_path)
    return result.fit_status, result.selected_weights, result.model_coefficients


if __name__ == "__main__":
    unittest.main()
