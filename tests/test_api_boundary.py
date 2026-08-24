from __future__ import annotations

import base64
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

from jsonschema import validate
from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from nestor_delta_service import app as app_module  # noqa: E402
from nestor_delta_service.boundary import RUN_STORE, RunStore  # noqa: E402
from nestor_delta_service.errors import SCHEMA_VERSION, analysis_failure  # noqa: E402
from nestor_delta_service.schema import ReportJsonV1, report_json_schema  # noqa: E402
from nestor_delta_web import render_logic as rl  # noqa: E402

FIXTURES = REPO_ROOT / "tests" / "ground_truth" / "fixtures"
MANIFEST = json.loads((FIXTURES / "manifest.json").read_text(encoding="utf-8"))


class ApiBoundaryV1Tests(unittest.TestCase):
    def setUp(self) -> None:
        RUN_STORE.clear()
        app_module.RUN_STORE = RUN_STORE
        self._ledger_dir = tempfile.TemporaryDirectory()
        self.ledger_path = Path(self._ledger_dir.name) / "ledger.jsonl"
        self._old_ledger_path = os.environ.get("NESTOR_RELATIONSHIP_LEDGER_PATH")
        os.environ["NESTOR_RELATIONSHIP_LEDGER_PATH"] = str(self.ledger_path)
        self.client = TestClient(app_module.create_app())

    def tearDown(self) -> None:
        if self._old_ledger_path is None:
            os.environ.pop("NESTOR_RELATIONSHIP_LEDGER_PATH", None)
        else:
            os.environ["NESTOR_RELATIONSHIP_LEDGER_PATH"] = self._old_ledger_path
        self._ledger_dir.cleanup()

    def test_capabilities_are_truthful(self) -> None:
        response = self.client.get("/api/v1/capabilities")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["api_version"], "v1")
        self.assertEqual(body["report_schema_version"], SCHEMA_VERSION)
        self.assertRegex(body["pipeline_version"], r"^s10\.sha256\.[0-9a-f]{12}$")
        # Source revision - NOT a deployment identity, and distinct from
        # pipeline_version. Resolution rules live in tests/test_build_identity.py.
        # Here the contract is only that the field is well formed and that
        # /health reports the same value. Whether it is "unknown" is a
        # deployment check the suite cannot make.
        self.assertRegex(body["source_revision"], r"^(?:[0-9a-f]{7,40}|unknown)$")
        health = self.client.get("/health")
        self.assertEqual(health.status_code, 200)
        self.assertEqual(health.json()["source_revision"], body["source_revision"])
        self.assertEqual(body["execution"], {"mode": "sync"})
        self.assertEqual(
            body["run_retention"],
            {"mode": "in_memory_process_lifetime", "max_runs": 100},
        )
        self.assertEqual(
            body["ledger"],
            {"enabled": True, "durable": True, "path": str(self.ledger_path)},
        )
        self.assertTrue(body["inputs"]["csv_upload"])
        self.assertIn("spain_retail_eurostat_2008_2025", body["inputs"]["bundled_cases"])
        self.assertEqual(body["eurostat"]["dataset_search"], False)
        self.assertEqual(
            body["eurostat"]["presets"],
            [
                {
                    "id": "es_industry_vs_construction_confidence",
                    "label": "ES industry vs construction confidence",
                    "dataset": "ei_bssi_m_r2",
                }
            ],
        )
        self.assertEqual(
            body["features"],
            {"pdf_export": False, "report_persistence": False, "sharing": False},
        )

    def test_cors_preflight_is_enabled(self) -> None:
        response = self.client.options(
            "/api/v1/capabilities",
            headers={
                "Origin": "https://insight.example",
                "Access-Control-Request-Method": "GET",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["access-control-allow-origin"], "*")

    def test_audit_and_snapshot_have_versioned_paths_and_legacy_aliases(self) -> None:
        payload = {"case_name": "spain_retail_eurostat_2008_2025"}

        versioned_audit = self.client.post("/api/v1/audit", json=payload)
        legacy_audit = self.client.post("/audit", json=payload)
        versioned_snapshot = self.client.post("/api/v1/snapshot", json=payload)
        legacy_snapshot = self.client.post("/snapshot", json=payload)

        self.assertEqual(versioned_audit.status_code, 200)
        self.assertEqual(legacy_audit.status_code, 200)
        self.assertEqual(versioned_audit.json(), legacy_audit.json())
        self.assertEqual(versioned_snapshot.status_code, 200)
        self.assertEqual(legacy_snapshot.status_code, 200)
        self.assertEqual(versioned_snapshot.json(), legacy_snapshot.json())

    def test_all_business_routes_use_the_auth_dependency(self) -> None:
        business_paths = {
            "/api/v1/runs",
            "/api/v1/runs/{run_id}",
            "/api/v1/capabilities",
            "/analyze",
            "/api/v1/audit",
            "/audit",
            "/api/v1/snapshot",
            "/snapshot",
        }

        checked = set()
        for route in self.client.app.routes:
            if route.path not in business_paths:
                continue
            dependency_calls = {item.call for item in route.dependant.dependencies}
            self.assertIn(app_module.allow_request, dependency_calls, route.path)
            checked.add(route.path)

        self.assertEqual(checked, business_paths)

    def test_post_run_returns_completed_envelope_and_get_returns_same_report(self) -> None:
        response = self.client.post(
            "/api/v1/runs",
            json=_ground_truth_payload("s_gt_1_positive"),
            headers={"X-Nestor-Client": "nestor-insight"},
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        run = body["run"]
        report = body["report"]
        self.assertEqual(run["status"], "completed")
        self.assertEqual(run["api_version"], "v1")
        self.assertEqual(run["client"], "nestor-insight")
        self.assertIsNone(run["requested_by"])
        self.assertIsNone(run["tenant_id"])
        self.assertEqual(report["schema_version"], SCHEMA_VERSION)
        self.assertEqual(report["producer"], "nestor-delta")
        self.assertRegex(report["pipeline_version"], r"^s10\.sha256\.[0-9a-f]{12}$")
        self.assertEqual(report["outcome"], "ok")
        self.assertEqual(
            report["configuration"]["evidence_gate"]["selection_terms"],
            ["FDR", "stability", "uncertainty", "sample_support"],
        )
        self.assertEqual(
            report["configuration"]["noise_floor"]["role"],
            "diagnostic_not_gate",
        )
        _validate_committed_schema(report)
        rel = next(item for item in report["relations"] if item["source"] == "true_driver")
        self.assertEqual(rel["effect"]["score"], 0.5844220533473201)
        self.assertFalse(set(run) & set(report))
        ledger_entries = [
            json.loads(line)
            for line in self.ledger_path.read_text(encoding="utf-8").splitlines()
        ]
        self.assertEqual(len(ledger_entries), report["selection"]["selected_count"])
        self.assertEqual(ledger_entries[0]["mode"], "realtime")
        self.assertEqual(ledger_entries[0]["run_id"], run["run_id"])
        self.assertEqual(ledger_entries[0]["snapshot_hash"], report["snapshot"]["hash"])
        self.assertEqual(ledger_entries[0]["source"], "true_driver")
        self.assertEqual(ledger_entries[0]["target"], report["case"]["target"])
        self.assertEqual(ledger_entries[0]["lag"], rel["lag"])
        self.assertEqual(ledger_entries[0]["sign"], rel["effect"]["sign"])
        self.assertEqual(ledger_entries[0]["score"], rel["effect"]["score"])
        self.assertEqual(ledger_entries[0]["stability"], rel["stability"])
        self.assertEqual(ledger_entries[0]["generated_as_of"], report["generated_as_of"])
        self.assertEqual(ledger_entries[0]["pipeline_version"], report["pipeline_version"])

        get_response = self.client.get(f"/api/v1/runs/{run['run_id']}")
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(get_response.json()["report"], report)

    def test_baseline_only_is_completed_200(self) -> None:
        response = self.client.post("/api/v1/runs", json=_ground_truth_payload("s_gt_2_negative"))

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["run"]["status"], "completed")
        self.assertEqual(body["report"]["outcome"], "baseline_only")
        self.assertEqual(body["report"]["selection"]["selected_count"], 0)
        self.assertFalse(self.ledger_path.exists())
        _validate_committed_schema(body["report"])

    def test_ledger_append_failure_does_not_fail_analysis(self) -> None:
        os.environ["NESTOR_RELATIONSHIP_LEDGER_PATH"] = self._ledger_dir.name

        response = self.client.post(
            "/api/v1/runs",
            json=_ground_truth_payload("s_gt_1_positive"),
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["run"]["status"], "completed")
        self.assertEqual(response.json()["report"]["outcome"], "ok")

    def test_validation_error_creates_no_run(self) -> None:
        before = len(RUN_STORE._items)
        response = self.client.post("/api/v1/runs", json={})

        self.assertEqual(response.status_code, 422)
        body = response.json()
        self.assertEqual(body["schema_version"], SCHEMA_VERSION)
        self.assertEqual(body["outcome"], "validation_error")
        self.assertNotIn("run", body)
        self.assertEqual(len(RUN_STORE._items), before)

    def test_pipeline_failure_keeps_failed_run(self) -> None:
        original = app_module.analyze_payload
        error = analysis_failure(
            "forced_failure",
            "Forced failure for API boundary test.",
            detail={"forced": True},
        ).to_report()

        def fake_analyze(_payload):
            return 500, error

        try:
            app_module.analyze_payload = fake_analyze
            response = self.client.post("/api/v1/runs", json={"case_name": "anything"})
        finally:
            app_module.analyze_payload = original

        self.assertEqual(response.status_code, 500)
        body = response.json()
        self.assertEqual(body["run"]["status"], "failed")
        self.assertIsNone(body["report"])
        self.assertEqual(body["schema_version"], SCHEMA_VERSION)
        self.assertEqual(body["outcome"], "analysis_failure")
        self.assertEqual(body["error"]["code"], "forced_failure")
        run_id = body["run"]["run_id"]
        self.assertEqual(self.client.get(f"/api/v1/runs/{run_id}").json(), body)

    def test_run_store_evicts_oldest_run(self) -> None:
        small = RunStore(max_runs=2)
        original = app_module.RUN_STORE
        try:
            app_module.RUN_STORE = small
            ids = []
            for _ in range(3):
                response = self.client.post(
                    "/api/v1/runs",
                    json=_ground_truth_payload("s_gt_2_negative"),
                )
                ids.append(response.json()["run"]["run_id"])

            self.assertEqual(self.client.get(f"/api/v1/runs/{ids[0]}").status_code, 404)
            self.assertEqual(self.client.get(f"/api/v1/runs/{ids[1]}").status_code, 200)
            self.assertEqual(self.client.get(f"/api/v1/runs/{ids[2]}").status_code, 200)
        finally:
            app_module.RUN_STORE = original

    def test_schema_artifact_and_reader_tolerate_unknown_enum_and_extra_field(self) -> None:
        schema_path = REPO_ROOT / "docs" / "report_json_v1.schema.json"
        fixture_path = REPO_ROOT / "docs" / "report_json_v1_unknown_enum_extra_fixture.json"
        self.assertTrue(schema_path.exists())
        self.assertEqual(
            json.loads(schema_path.read_text(encoding="utf-8")),
            report_json_schema(),
        )

        fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
        ReportJsonV1.model_validate(fixture)
        _validate_committed_schema(fixture)
        view = rl.relation_view(fixture["relations"][0])
        self.assertEqual(view["reason_code"], "future_reason_code")
        self.assertEqual(view["lifecycle"]["state"], "new_future_state")
        self.assertEqual(rl.classify_response(200, fixture), "report_baseline")


def _ground_truth_payload(name: str) -> dict:
    item = MANIFEST["fixtures"][name]
    payload = dict(item["request"])
    payload["csv_base64"] = base64.b64encode((FIXTURES / item["file"]).read_bytes()).decode(
        "ascii"
    )
    return payload


def _validate_committed_schema(report: dict) -> None:
    schema = json.loads((REPO_ROOT / "docs" / "report_json_v1.schema.json").read_text())
    validate(instance=report, schema=schema)


if __name__ == "__main__":
    unittest.main()
