"""W4 frontend contract/state tests — no live backend, no Streamlit needed.

Drives render_logic against docs/mock_reports_v1.json to prove the frontend maps
every canonical state correctly and never (a) shows null as 0, (b) collapses an
error or baseline_only into "No data", or (c) fabricates charts.
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SRC = REPO / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from nestor_delta_web import presets, render_logic as rl  # noqa: E402

MOCKS = json.loads((REPO / "docs" / "mock_reports_v1.json").read_text())


def _assert_analyst_columns(columns):
    assert "sample support" in columns
    assert columns[-1] == "noise floor (diagnostic)"


# canonical mock key -> (http_status, expected view)
CASES = {
    "snapshot_ready__eurostat": (200, "snapshot_ready"),
    "audit_ok__spain_retail": (200, "audit_ok"),
    "baseline_only__spain_retail": (200, "report_baseline"),
    "ok__with_selection": (200, "report_ok"),
    "validation_error__missing_month": (422, "validation_error"),
    "validation_error__rejected_transform": (422, "validation_error"),
    "analysis_failure__singular": (500, "analysis_failure"),
    "not_found__unknown_case": (404, "not_found"),
}


class ViewClassification(unittest.TestCase):
    def test_every_canonical_state_maps_to_expected_view(self):
        for key, (status, expected) in CASES.items():
            body = MOCKS[key]
            self.assertEqual(rl.classify_response(status, body), expected,
                             f"{key} should classify as {expected}")

    def test_baseline_only_is_not_an_error(self):
        body = MOCKS["baseline_only__spain_retail"]
        view = rl.classify_response(200, body)
        self.assertEqual(view, "report_baseline")
        self.assertFalse(rl.is_error_view(view))

    def test_error_classes_are_distinct_and_not_baseline(self):
        views = {k: rl.classify_response(s, MOCKS[k]) for k, (s, _) in CASES.items()
                 if k.startswith(("validation", "analysis", "not_found"))}
        self.assertEqual(len(set(views.values())), 3)  # all distinct
        for v in views.values():
            self.assertTrue(rl.is_error_view(v))
            self.assertNotEqual(v, "report_baseline")

    def test_transport_failures_and_malformed(self):
        self.assertEqual(rl.classify_response(None, None, transport="unreachable"), "unreachable")
        self.assertEqual(rl.classify_response(None, None, transport="timeout"), "timeout")
        self.assertEqual(rl.classify_response(200, {"outcome": "ok"}), "malformed")  # no schema_version
        self.assertEqual(rl.classify_response(200, {"schema_version": "delta.report.v1"}), "malformed")
        self.assertEqual(rl.classify_response(200, "not a dict"), "malformed")


class NullNeverZero(unittest.TestCase):
    def test_baseline_confidence_is_null_not_zero(self):
        conf = rl.confidence_display(MOCKS["baseline_only__spain_retail"])
        self.assertTrue(conf["is_null"])
        self.assertIsNone(conf["value"])
        self.assertNotEqual(conf["text"], "0")
        self.assertNotIn("0%", conf["text"])
        self.assertIn("insufficient", conf["text"].lower())

    def test_present_confidence_renders_percent(self):
        conf = rl.confidence_display(MOCKS["ok__with_selection"])
        self.assertFalse(conf["is_null"])
        self.assertTrue(conf["text"].endswith("%"))

    def test_null_value_formats_as_dash_never_zero(self):
        # The guarantee is in the formatter, independent of mock contents.
        self.assertEqual(rl.fmt_number(None), "—")
        self.assertNotEqual(rl.fmt_number(None), "0")
        self.assertNotEqual(rl.fmt_number(None), "0.000")
        self.assertEqual(rl.fmt_signed(None), "—")
        self.assertEqual(rl.fmt_percent(None), "—")
        # a real 0 is still shown as 0, only null becomes a dash
        self.assertEqual(rl.fmt_number(0.0), "0.000")

    def test_tiny_p_value_formats_as_bound_not_zero(self):
        self.assertEqual(rl.fmt_p_value(0.0), "< 1e-12")
        self.assertNotEqual(rl.fmt_p_value(0.0), "0.0000")
        self.assertEqual(rl.fmt_p_value(1e-300), "< 1e-12")
        self.assertNotEqual(rl.fmt_p_value(1e-300), "0.0000")
        self.assertEqual(rl.fmt_p_value(0.00003), "3.0e-05")
        self.assertNotEqual(rl.fmt_p_value(0.00003), "0.0000")
        self.assertEqual(rl.fmt_p_value(None), "—")

    def test_nullable_selected_is_preserved(self):
        relation = dict(MOCKS["baseline_only__spain_retail"]["relations"][0])
        relation["selected"] = None
        self.assertIsNone(rl.relation_view(relation)["selected"])


class NoFabrication(unittest.TestCase):
    def test_trajectory_shown_only_when_present(self):
        ok_rels = MOCKS["ok__with_selection"]["relations"]
        has = [r for r in ok_rels if rl.should_show_trajectory(r)]
        empty = [r for r in ok_rels if not rl.should_show_trajectory(r)]
        self.assertTrue(has)      # at least one real trajectory
        # relations with [] or null trajectory must not be shown
        for r in empty:
            self.assertIn(r.get("trajectory"), (None, [], ))

    def test_baseline_relations_have_no_fake_trajectory(self):
        for r in MOCKS["baseline_only__spain_retail"]["relations"]:
            self.assertFalse(rl.should_show_trajectory(r))

    def test_evaluation_guard(self):
        self.assertTrue(rl.should_show_evaluation(MOCKS["ok__with_selection"]))
        # a report with null evaluation must not show an interval
        self.assertIsNone(rl.evaluation_interval({"evaluation": None}))


class TransformGate(unittest.TestCase):
    def test_accepted_diagnostics_allow_analyze(self):
        diags = MOCKS["audit_ok__spain_retail"]["transform_diagnostics"]
        self.assertEqual(rl.transform_conflicts(diags), [])
        self.assertTrue(rl.analyze_allowed(diags))

    def test_rejected_diagnostic_blocks_analyze(self):
        diags = [{"signal": "hicp", "declared": "none",
                  "highly_persistent_risk": True, "verdict": "rejected"}]
        self.assertEqual(rl.transform_conflicts(diags), ["hicp"])
        self.assertFalse(rl.analyze_allowed(diags))


class Lifecycle(unittest.TestCase):
    def test_raw_states_preserved(self):
        for state in (
            "insufficient_evidence",
            "birth",
            "strengthening",
            "stable",
            "decaying",
            "dead",
        ):
            self.assertEqual(rl.lifecycle_badge(state)["state"], state)
        # decaying is a fact, not an alarm -> warn tone, not "critical"
        self.assertEqual(rl.lifecycle_badge("decaying")["tone"], "warn")

    def test_lifecycle_track_has_one_active_reported_state(self):
        steps = rl.lifecycle_steps("decaying")
        self.assertEqual(
            [step["state"] for step in steps],
            [
                "insufficient_evidence",
                "birth",
                "strengthening",
                "stable",
                "decaying",
                "dead",
            ],
        )
        self.assertEqual(
            [step["state"] for step in steps if step["active"]],
            ["decaying"],
        )

    def test_relation_expander_pairs_lifecycle_with_stability(self):
        view = rl.relation_view(MOCKS["ok__with_selection"]["relations"][0])
        label = rl.relation_expander_label(view)
        self.assertIn(view["lifecycle"]["label"], label)
        self.assertIn("stability", label)
        self.assertIn(rl.fmt_number(view["stability"]), label)


class ConfigurationDisplay(unittest.TestCase):
    def test_old_reports_without_configuration_stay_quiet(self):
        self.assertEqual(rl.configuration_rows(MOCKS["ok__with_selection"]), [])

    def test_effective_configuration_is_exposed_as_rows(self):
        report = {
            "configuration": {
                "reproducibility": {"rule": "same three inputs -> same report"},
                "inputs": {
                    "source": "case",
                    "train_end": "2023-12",
                    "lag_window": 3,
                    "candidate_count": 2,
                    "train_observations": 192,
                    "transform_declarations": {"target": "diff", "signal": "log_diff"},
                },
                "effect": {
                    "score_scope": "full_train_window",
                    "ranking": "score_descending_then_source",
                },
                "rolling_lifecycle": {
                    "window_rule": "min(36, max(lag_window + 6, train_observations // 3))",
                    "effective_window": 36,
                    "step_interval": 6,
                    "state_rule": "S9 end-of-sample trajectory classifier",
                },
                "noise_floor": {
                    "role": "diagnostic_not_gate",
                    "comparisons_rule": "lag_window * candidate_count",
                    "comparisons": 6,
                    "alpha": 0.05,
                },
                "evidence_gate": {
                    "selection_terms": ["FDR", "stability", "uncertainty", "sample_support"],
                    "alpha": 0.05,
                    "min_stability": 0.45,
                    "max_uncertainty": 0.2,
                    "min_sample_support": 0.5,
                },
            }
        }
        rows = rl.configuration_rows(report)
        rendered = {(row["section"], row["setting"]): row["value"] for row in rows}
        self.assertEqual(rendered[("Inputs", "Lag window")], "3")
        self.assertEqual(rendered[("Rolling lifecycle", "Effective window")], "36")
        self.assertEqual(rendered[("Evidence gate", "Minimum stability")], "0.45")
        self.assertIn("stability", rendered[("Evidence gate", "Selection terms")])
        self.assertIn("signal=log_diff", rendered[("Inputs", "Transform declarations")])


class UserReportSummary(unittest.TestCase):
    def test_baseline_report_is_a_successful_baseline_decision(self):
        report = MOCKS["baseline_only__spain_retail"]
        decision = rl.report_decision(report)
        self.assertEqual(decision["tone"], "baseline")
        self.assertEqual(decision["selected_count"], 0)
        self.assertTrue(decision["confidence"]["is_null"])
        self.assertNotIn("error", decision["headline"].lower())
        self.assertIn("intended behavior", decision["success_statement"].lower())

    def test_selected_report_keeps_backend_narrative_and_confidence(self):
        report = MOCKS["ok__with_selection"]
        decision = rl.report_decision(report)
        self.assertEqual(decision["tone"], "selected")
        self.assertEqual(decision["headline"], report["narrative"]["headline"])
        self.assertEqual(decision["selected_count"], report["selection"]["selected_count"])
        self.assertFalse(decision["confidence"]["is_null"])

    def test_report_context_and_download_name_use_contract_fields(self):
        report = MOCKS["ok__with_selection"]
        context = rl.report_context(report)
        self.assertEqual(context["target"], report["case"]["target"])
        self.assertEqual(context["generated_as_of"], report["generated_as_of"])
        self.assertEqual(context["snapshot_hash"], report["snapshot"]["hash"])
        filename = rl.report_filename(report)
        self.assertTrue(filename.startswith("nestor-delta-"))
        self.assertTrue(filename.endswith(".json"))
        self.assertNotIn(" ", filename)


class PresentationHierarchy(unittest.TestCase):
    def test_p0_answers_follow_the_accepted_order(self):
        answers = rl.report_p0_answers(MOCKS["baseline_only__spain_retail"])

        self.assertEqual(tuple(answers), rl.P0_ANSWER_ORDER)
        self.assertEqual(answers["run_status"], "Analysis completed successfully")
        self.assertEqual(answers["selection"]["candidate_count"], 4)
        self.assertEqual(answers["selection"]["selected_count"], 0)
        self.assertEqual(answers["selection"]["rejected_count"], 4)

    def test_gate_explanation_is_concise_and_does_not_claim_reliability(self):
        explanation = rl.EVIDENCE_GATE_EXPLANATION

        self.assertLessEqual(len(explanation.split()), 15)
        self.assertNotIn("reliable", explanation.lower())
        self.assertIn("FDR", explanation)
        self.assertIn("sample support", explanation)

    def test_relation_evidence_exposes_direction_lag_and_strength_before_reason(self):
        answers = rl.report_p0_answers(MOCKS["ok__with_selection"])
        relation = answers["relation_evidence"][0]
        reason = answers["gate_reasons"][0]

        self.assertEqual(relation["direction"], "positive")
        self.assertEqual(relation["lag"], 3)
        self.assertEqual(relation["score"], 0.58)
        self.assertEqual(reason["reason_code"], "selected")

    def test_context_bar_promotes_pipeline_with_case_as_of_and_snapshot(self):
        report = dict(MOCKS["ok__with_selection"])
        report["pipeline_version"] = "s10.sha256.testvalue123"

        items = rl.context_bar_items(report)

        self.assertEqual(
            [item["label"] for item in items],
            ["Case", "As of", "Snapshot", "Pipeline"],
        )
        self.assertEqual(items[-1]["value"], report["pipeline_version"])


class AnalystTableGuard(unittest.TestCase):
    def test_clean_table_has_sample_support_and_diagnostic_last(self):
        rows = rl.analyst_table_rows(MOCKS["ok__with_selection"])

        self.assertTrue(rows)
        self.assertEqual(tuple(rows[0]), rl.ANALYST_TABLE_COLUMNS)
        _assert_analyst_columns(tuple(rows[0]))

    def test_guard_rejects_in_memory_column_drift(self):
        drifted = tuple(
            column
            for column in rl.ANALYST_TABLE_COLUMNS
            if column != "sample support"
        )

        with self.assertRaises(AssertionError):
            _assert_analyst_columns(drifted)


class SnapshotDownload(unittest.TestCase):
    def test_snapshot_surfaces_hash_columns_rows(self):
        s = rl.snapshot_summary(MOCKS["snapshot_ready__eurostat"])
        self.assertIsNotNone(s["hash"])
        self.assertTrue(s["columns"])
        self.assertIsNotNone(s["row_count"])

    def test_snapshot_becomes_hash_bound_upload_payload(self):
        snapshot = MOCKS["snapshot_ready__eurostat"]
        source = {
            "eurostat": {"series": []},
            "target": "retail_volume",
            "candidate_signals": ["industrial_production"],
            "transform_declarations": {
                "retail_volume": "diff",
                "industrial_production": "diff",
            },
            "train_end": "2023-12",
            "lag_window": 2,
        }

        frozen = rl.frozen_snapshot_payload(snapshot, source)

        self.assertNotIn("eurostat", frozen)
        self.assertEqual(frozen["csv_base64"], snapshot["csv_base64"])
        self.assertEqual(frozen["date_column"], snapshot["columns"][0])


class Presets(unittest.TestCase):
    def test_bundled_cases_match_backend_supported_cases(self):
        self.assertEqual(
            presets.BUNDLED_CASES,
            (
                "spain_retail_eurostat_2008_2025",
                "spain_retail_eurostat_expanded_2008_2025",
                "spain_industrial_production_eurostat_2008_2023",
            ),
        )


class Isolation(unittest.TestCase):
    def test_frontend_never_imports_nestor_delta(self):
        web = REPO / "src" / "nestor_delta_web"
        for py in web.glob("*.py"):
            text = py.read_text()
            self.assertNotIn("import nestor_delta", text, f"{py.name} imports nestor_delta")
            self.assertNotIn("from nestor_delta ", text, f"{py.name} imports from nestor_delta")
            self.assertNotIn("from nestor_delta.", text, f"{py.name} imports from nestor_delta")


if __name__ == "__main__":
    unittest.main()
