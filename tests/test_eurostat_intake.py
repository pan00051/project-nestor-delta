from __future__ import annotations

import sys
import unittest
import base64
import hashlib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from nestor_delta_service.adapter import (  # noqa: E402
    analyze_payload,
    audit_payload,
    snapshot_payload,
)
from nestor_delta_service.eurostat import (  # noqa: E402
    EurostatSeriesSpec,
    build_eurostat_snapshot,
    eurostat_url,
    extract_jsonstat_series,
)


class EurostatIntakeTests(unittest.TestCase):
    def test_build_snapshot_from_local_jsonstat_payloads(self) -> None:
        snapshot = build_eurostat_snapshot(_eurostat_payload())

        self.assertEqual(snapshot.dates[0], "2020-01")
        self.assertEqual(snapshot.dates[-1], "2023-12")
        self.assertEqual(len(snapshot.rows), 48)
        self.assertEqual(len(snapshot.snapshot_hash), 64)
        self.assertEqual(snapshot.provenance["source"], "eurostat")
        self.assertEqual(snapshot.signal_metadata["target"]["unit"], "I21")
        self.assertEqual(snapshot.signal_metadata["target"]["seasonal_adjustment"], "SCA")
        self.assertEqual(snapshot.signal_metadata["source"]["unit"], "BAL")
        self.assertEqual(snapshot.signal_metadata["source"]["seasonal_adjustment"], "SA")

    def test_audit_and_analyze_accept_eurostat_source(self) -> None:
        payload = {
            "eurostat": _eurostat_payload(),
            "target": "target",
            "candidate_signals": ["source"],
            "transform_declarations": {"target": "diff", "source": "diff"},
            "train_end": "2023-12",
            "lag_window": 1,
        }

        audit_status, audit_report = audit_payload(payload)
        analyze_status, analyze_report = analyze_payload(payload)

        self.assertEqual(audit_status, 200)
        self.assertEqual(audit_report["outcome"], "ok_to_analyze")
        self.assertEqual(audit_report["snapshot"]["source"], "eurostat")
        self.assertEqual(audit_report["data_audit"]["date_axis"]["expected_months"], 48)
        self.assertEqual(analyze_status, 200)
        self.assertIn(analyze_report["outcome"], {"ok", "baseline_only"})
        self.assertEqual(
            audit_report["snapshot"]["hash"],
            analyze_report["snapshot"]["hash"],
        )
        self.assertEqual(
            audit_report["data_audit"],
            analyze_report["data_audit"],
        )

    def test_snapshot_endpoint_exports_hash_bound_csv(self) -> None:
        status, report = snapshot_payload(
            {
                "eurostat": _eurostat_payload(),
                "target": "target",
                "candidate_signals": ["source"],
                "transform_declarations": {"target": "diff", "source": "diff"},
                "train_end": "2023-12",
                "lag_window": 1,
            }
        )

        self.assertEqual(status, 200)
        self.assertEqual(report["outcome"], "snapshot_ready")
        self.assertEqual(report["snapshot"]["source"], "eurostat")
        self.assertEqual(report["row_count"], 48)
        self.assertEqual(report["columns"], ["date", "target", "source"])
        self.assertEqual(len(report["snapshot"]["hash"]), 64)
        csv_text = base64.b64decode(report["csv_base64"]).decode("utf-8")
        self.assertTrue(csv_text.startswith("date,target,source\n"))
        self.assertEqual(
            hashlib.sha256(csv_text.encode("utf-8")).hexdigest(),
            report["snapshot"]["hash"],
        )

    def test_eurostat_source_is_part_of_exactly_one_source_rule(self) -> None:
        status, report = audit_payload({"case_name": "x", "eurostat": _eurostat_payload()})

        self.assertEqual(status, 422)
        self.assertEqual(report["error"]["code"], "invalid_source")

    def test_eurostat_missing_month_fails_before_analysis(self) -> None:
        payload = _eurostat_payload(end="2020-03", months=("2020-01", "2020-03"))

        status, report = audit_payload(
            {
                "eurostat": payload,
                "target": "target",
                "candidate_signals": ["source"],
                "transform_declarations": {"target": "diff", "source": "diff"},
                "train_end": "2020-03",
                "lag_window": 1,
            }
        )

        self.assertEqual(status, 422)
        self.assertEqual(report["error"]["code"], "invalid_eurostat_request")
        self.assertIn("exact 2020-01..2020-03 monthly axis", report["error"]["message"])

    def test_eurostat_unknown_requested_signal_is_validation_error(self) -> None:
        payload = {
            "eurostat": _eurostat_payload(),
            "target": "target",
            "candidate_signals": ["missing_source"],
            "transform_declarations": {"target": "diff", "missing_source": "diff"},
            "train_end": "2023-12",
            "lag_window": 1,
        }

        status, report = audit_payload(payload)

        self.assertEqual(status, 422)
        self.assertEqual(report["error"]["code"], "unknown_signal")

    def test_jsonstat_extraction_requires_selected_dimension_codes(self) -> None:
        spec = EurostatSeriesSpec(
            name="source",
            dataset="demo",
            filters=(("freq", "M"), ("geo", "ES"), ("unit", "BAL")),
        )
        extracted = extract_jsonstat_series(_jsonstat(("2020-01", "2020-02"), 1.0), spec)

        self.assertEqual(extracted, (("2020-01", 1.0), ("2020-02", 2.0)))

    def test_url_is_stable_and_contains_time_bounds(self) -> None:
        spec = EurostatSeriesSpec(
            name="source",
            dataset="demo_dataset",
            filters=(("freq", "M"), ("geo", "ES")),
        )

        url = eurostat_url(spec, "2020-01", "2020-12")

        self.assertIn("/demo_dataset?", url)
        self.assertIn("freq=M", url)
        self.assertIn("geo=ES", url)
        self.assertIn("sinceTimePeriod=2020-01", url)
        self.assertIn("untilTimePeriod=2020-12", url)


def _eurostat_payload(
    *,
    end: str = "2023-12",
    months: tuple[str, ...] | None = None,
) -> dict[str, object]:
    if months is None:
        months = tuple(
            f"{2020 + index // 12:04d}-{index % 12 + 1:02d}"
            for index in range(48)
        )
    return {
        "start": "2020-01",
        "end": end,
        "series": [
            {
                "name": "target",
                "dataset": "target_dataset",
                "filters": {"freq": "M", "geo": "ES", "s_adj": "SCA", "unit": "I21"},
            },
            {
                "name": "source",
                "dataset": "source_dataset",
                "filters": {"freq": "M", "geo": "ES", "s_adj": "SA", "unit": "BAL"},
            },
        ],
        "snapshots": {
            "target": _jsonstat(months, 10.0),
            "source": _jsonstat(months, 20.0),
        },
    }


def _jsonstat(months: tuple[str, ...], base: float) -> dict[str, object]:
    return {
        "id": ["freq", "geo", "s_adj", "unit", "time"],
        "size": [1, 1, 1, 1, len(months)],
        "dimension": {
            "freq": {"category": {"index": {"M": 0}}},
            "geo": {"category": {"index": {"ES": 0}}},
            "s_adj": {"category": {"index": {"SCA": 0, "SA": 0}}},
            "unit": {"category": {"index": {"I21": 0, "BAL": 0}}},
            "time": {"category": {"index": {month: index for index, month in enumerate(months)}}},
        },
        "value": [base + index for index, _ in enumerate(months)],
        "updated": "2026-08-19T00:00:00+0000",
    }


if __name__ == "__main__":
    unittest.main()
