from __future__ import annotations

import base64
import hashlib
import json
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from nestor_delta_service.adapter import analyze_payload, audit_payload, snapshot_payload  # noqa: E402
from nestor_delta_service.errors import SCHEMA_VERSION  # noqa: E402


class WebsiteContractTests(unittest.TestCase):
    def test_mock_reports_follow_report_json_v1_contract(self) -> None:
        path = REPO_ROOT / "docs" / "mock_reports_v1.json"
        payload = json.loads(path.read_text())

        self.assertIn("snapshot_ready__eurostat", payload)
        self.assertIn("audit_ok__spain_retail", payload)
        self.assertIn("baseline_only__spain_retail", payload)
        self.assertIn("ok__with_selection", payload)
        self.assertIn("validation_error__missing_month", payload)
        self.assertIn("validation_error__rejected_transform", payload)
        self.assertIn("analysis_failure__singular", payload)
        self.assertIn("not_found__unknown_case", payload)
        for name, report in payload.items():
            if name == "_note":
                continue
            self.assertEqual(report["schema_version"], SCHEMA_VERSION)
            self.assertNotIn("report_version", report)
            if "case" in report:
                self.assertIn("lag_window", report["case"])
                self.assertNotIn("max_lag", report["case"])
            if report["outcome"] in {"ok_to_analyze", "ok", "baseline_only"}:
                self.assertIsNotNone(report["data_audit"])
                self.assertIn("transform_diagnostics", report)
                self.assertEqual(len(report["snapshot"]["hash"]), 64)
            if report["outcome"] == "snapshot_ready":
                self.assertEqual(report["snapshot"]["source"], "eurostat")
                self.assertEqual(len(report["snapshot"]["hash"]), 64)
                self.assertIn("csv_base64", report)
                csv_bytes = base64.b64decode(report["csv_base64"], validate=True)
                csv_lines = csv_bytes.decode("utf-8").splitlines()
                self.assertEqual(
                    hashlib.sha256(csv_bytes).hexdigest(),
                    report["snapshot"]["hash"],
                )
                self.assertEqual(csv_lines[0].split(","), report["columns"])
                self.assertEqual(len(csv_lines) - 1, report["row_count"])

    def test_analyze_bundled_case_returns_report_not_no_data(self) -> None:
        status, report = analyze_payload({"case_name": "spain_retail_eurostat_2008_2025"})

        self.assertEqual(status, 200)
        self.assertEqual(report["schema_version"], SCHEMA_VERSION)
        self.assertIn(report["outcome"], {"ok", "baseline_only"})
        self.assertIn("relations", report)
        self.assertIn("selection", report)
        self.assertEqual(len(report["snapshot"]["hash"]), 64)
        self.assertIn("lag_window", report["case"])
        self.assertNotIn("report_version", report)
        self.assertNotIn("max_lag", report["case"])
        self.assertIsNotNone(report["data_audit"])
        self.assertTrue(report["transform_diagnostics"])

    def test_audit_bundled_case_returns_data_audit_before_analysis(self) -> None:
        status, report = audit_payload({"case_name": "spain_retail_eurostat_2008_2025"})

        self.assertEqual(status, 200)
        self.assertEqual(report["schema_version"], SCHEMA_VERSION)
        self.assertEqual(report["outcome"], "ok_to_analyze")
        self.assertEqual(
            report["data_audit"]["date_axis"],
            {
                "continuous": True,
                "expected_months": 216,
                "present": 216,
                "missing_months": [],
                "duplicate_months": [],
            },
        )
        risky = {
            item["signal"]
            for item in report["transform_diagnostics"]
            if item["highly_persistent_risk"]
        }
        self.assertEqual(risky, {"unemployment_rate", "hicp"})
        self.assertTrue(
            all(item["verdict"] == "accepted" for item in report["transform_diagnostics"])
        )

    def test_audit_and_analyze_share_data_audit_blocks_byte_for_byte(self) -> None:
        payload = {"case_name": "spain_retail_eurostat_2008_2025"}
        audit_status, audit_report = audit_payload(payload)
        analyze_status, analyze_report = analyze_payload(payload)

        self.assertEqual(audit_status, 200)
        self.assertEqual(analyze_status, 200)
        self.assertEqual(audit_report["data_audit"], analyze_report["data_audit"])
        self.assertEqual(
            audit_report["transform_diagnostics"],
            analyze_report["transform_diagnostics"],
        )

    def test_unknown_case_is_not_found_not_empty_data(self) -> None:
        status, report = analyze_payload({"case_name": "missing_case"})

        self.assertEqual(status, 404)
        self.assertEqual(report["schema_version"], SCHEMA_VERSION)
        self.assertEqual(report["outcome"], "not_found")
        self.assertEqual(report["error"]["code"], "case_not_found")

    def test_exactly_one_source_is_required(self) -> None:
        status, report = analyze_payload({})

        self.assertEqual(status, 422)
        self.assertEqual(report["outcome"], "validation_error")
        self.assertEqual(report["error"]["code"], "invalid_source")

    def test_upload_missing_month_is_validation_error(self) -> None:
        csv_text = "\n".join(
            [
                "date,target,source",
                "2020-01,1.0,1.0",
                "2020-03,2.0,2.0",
            ]
        )

        status, report = audit_payload(
            {
                "csv_base64": _b64(csv_text),
                "target": "target",
                "candidate_signals": ["source"],
                "transform_declarations": {"target": "diff", "source": "diff"},
                "train_end": "2020-03",
                "lag_window": 1,
            }
        )

        self.assertEqual(status, 422)
        self.assertEqual(report["outcome"], "validation_error")
        self.assertEqual(report["error"]["code"], "non_contiguous_dates")
        self.assertEqual(report["error"]["detail"]["missing_months"], ["2020-02"])
        self.assertEqual(report["data_audit"]["date_axis"]["missing_months"], ["2020-02"])

    def test_upload_duplicate_month_is_validation_error_with_audit_detail(self) -> None:
        csv_text = "\n".join(
            [
                "date,target,source",
                "2020-01,1.0,1.0",
                "2020-01,1.5,1.5",
                "2020-02,2.0,2.0",
            ]
        )

        status, report = audit_payload(
            {
                "csv_base64": _b64(csv_text),
                "target": "target",
                "candidate_signals": ["source"],
                "transform_declarations": {"target": "diff", "source": "diff"},
                "train_end": "2020-02",
                "lag_window": 1,
            }
        )

        self.assertEqual(status, 422)
        self.assertEqual(report["error"]["code"], "duplicate_month")
        self.assertEqual(report["data_audit"]["date_axis"]["duplicate_months"], ["2020-01"])

    def test_high_persistence_none_is_rejected_in_audit_and_analyze(self) -> None:
        payload = {
            "case_name": "spain_retail_eurostat_2008_2025",
            "transform_declarations": {
                "retail_volume": "diff",
                "unemployment_rate": "diff",
                "consumer_confidence": "diff",
                "industrial_production": "diff",
                "hicp": "none",
            },
        }

        for runner in (audit_payload, analyze_payload):
            status, report = runner(payload)
            self.assertEqual(status, 422)
            self.assertEqual(report["outcome"], "validation_error")
            self.assertEqual(report["error"]["code"], "high_persistence_requires_transform")
            rejected = [
                item
                for item in report["transform_diagnostics"]
                if item["verdict"] == "rejected"
            ]
            self.assertEqual([item["signal"] for item in rejected], ["hicp"])

    def test_upload_empty_data_is_validation_error(self) -> None:
        status, report = analyze_payload(
            {
                "csv_base64": _b64("date,target,source\n"),
                "target": "target",
                "candidate_signals": ["source"],
                "transform_declarations": {"target": "diff", "source": "diff"},
                "train_end": "2020-03",
                "lag_window": 1,
            }
        )

        self.assertEqual(status, 422)
        self.assertEqual(report["error"]["code"], "too_few_observations")

    def test_upload_valid_snapshot_runs_synchronously(self) -> None:
        rows = ["date,target,source"]
        for index in range(48):
            year = 2020 + index // 12
            month = index % 12 + 1
            source = 10.0 + index * 0.3 + (1.0 if index % 5 == 0 else 0.0)
            target = 5.0 + index * 0.2 + (0.7 if (index - 1) % 5 == 0 else 0.0)
            rows.append(f"{year:04d}-{month:02d},{target:.4f},{source:.4f}")

        status, report = analyze_payload(
            {
                "csv_base64": _b64("\n".join(rows)),
                "target": "target",
                "candidate_signals": ["source"],
                "transform_declarations": {"target": "diff", "source": "diff"},
                "train_end": "2023-12",
                "lag_window": 1,
            }
        )

        self.assertEqual(status, 200)
        self.assertIn(report["outcome"], {"ok", "baseline_only"})
        self.assertEqual(report["snapshot"]["source"], "upload")
        audit_status, audit_report = audit_payload(
            {
                "csv_base64": _b64("\n".join(rows)),
                "target": "target",
                "candidate_signals": ["source"],
                "transform_declarations": {"target": "diff", "source": "diff"},
                "train_end": "2023-12",
                "lag_window": 1,
            }
        )
        self.assertEqual(audit_status, 200)
        self.assertEqual(len(report["snapshot"]["hash"]), 64)
        self.assertEqual(
            report["snapshot"]["hash"], audit_report["snapshot"]["hash"]
        )
        for signal in audit_report["data_audit"]["signals"]:
            self.assertEqual(signal["unit"], "unknown")
            self.assertEqual(signal["seasonal_adjustment"], "unknown")

    def test_upload_accepts_utf8_bom_on_csv_intake(self) -> None:
        rows = ["date,target,source"]
        for index in range(14):
            month = index + 1
            year = 2020 + (month - 1) // 12
            month_of_year = (month - 1) % 12 + 1
            rows.append(f"{year:04d}-{month_of_year:02d},{index + 1}.0,{index + 2}.0")
        csv_text = "\n".join(rows)

        payload = {
            "csv_base64": base64.b64encode(
                csv_text.encode("utf-8-sig")
            ).decode("ascii"),
            "target": "target",
            "candidate_signals": ["source"],
            "transform_declarations": {"target": "diff", "source": "diff"},
            "train_end": "2020-12",
            "lag_window": 1,
        }

        status, report = audit_payload(payload)
        snapshot_status, snapshot_report = snapshot_payload(payload)

        self.assertEqual(status, 200)
        self.assertEqual(snapshot_status, 200)
        self.assertEqual(snapshot_report["columns"][0], "date")

    def test_fastapi_module_imports_without_fastapi_dependency(self) -> None:
        import nestor_delta_service.app as app_module

        if app_module.FastAPI is None:
            self.assertIsNone(app_module.app)
        else:
            self.assertIsNotNone(app_module.app)


def _b64(text: str) -> str:
    return base64.b64encode(text.encode("utf-8")).decode("ascii")


if __name__ == "__main__":
    unittest.main()
