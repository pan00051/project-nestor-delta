"""
Nestor Delta — M0 evidence-calibration tests.

These are the two controls that decide whether the evidence gate can be trusted
at all. Everything downstream (UI, deployment, API) packages whatever these
tests say the gate is.

    S-GT-0   fixture integrity     — the ground truth has not silently moved
    S-GT-1   positive control      — an injected relation MUST be selected
    S-GT-2   negative control      — pure noise MUST NOT be selected
    S-GT-2b  false-positive rate   — multi-seed, marked slow
    S-GT-3   determinism           — same input -> byte-identical report

A detector that selects nothing and a detector that selects everything are
equally broken. S-GT-1 alone cannot tell them apart, which is why S-GT-2 is not
optional.

IMPORTANT — what S-GT-1 is: a CALIBRATION POSITIVE CONTROL. The relationship in
it was injected by `generate_ground_truth.py` so the detector's response to a
known answer can be measured. It is NOT a real-world causal case; `true_driver`
does not cause anything outside that file, and Delta detects statistical
relationships that survive its tests, not causation. If this fixture is ever
shown to an audience it must be presented as a ground-truth check on the
instrument.

All assertions key off `Report JSON v1` (WEBSITE_CONTRACT_W0.md), never off
internal function names, so the controls survive refactoring of S1-S10. The only
code that needs adapting to this repo is `run_report()` below.

Run against the API instead of in-process:
    NESTOR_API_BASE=http://localhost:8000 pytest tests/test_ground_truth.py
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"
MANIFEST = json.loads((FIXTURES / "manifest.json").read_text(encoding="utf-8"))
SPEC = MANIFEST["spec"]

REJECTION_CODES = {
    "below_fdr_corrected_effect",
    "insufficient_stability",
    "excess_relationship_uncertainty",
    "insufficient_sample_support",
    "not_selected",
}


# --------------------------------------------------------------- THE ADAPTER
# The ONE place to wire this suite into the repo. Everything else is contract.
def run_report(csv_path: Path, request: dict) -> dict:
    """Run the pipeline on a fixture CSV and return one Report JSON v1 dict."""
    api_base = os.environ.get("NESTOR_API_BASE")
    payload = dict(request)
    payload["csv_base64"] = base64.b64encode(csv_path.read_bytes()).decode("ascii")

    if api_base:
        import requests  # noqa: PLC0415

        resp = requests.post(f"{api_base}/api/v1/runs", json=payload, timeout=300)
        # A legal-empty result is a 200. If this ever asserts, the API is
        # misclassifying `baseline_only` as an error -- see W0 section 1.
        assert resp.status_code in (200, 422, 500), resp.status_code
        return resp.json()                     # envelope or bare report; unwrapped below

    from nestor_delta_service.adapter import analyze_payload  # noqa: PLC0415

    status, report = analyze_payload(payload)
    if report.get("outcome") in {"ok", "baseline_only"}:
        assert status == 200, status
    return report


# ------------------------------------------------------------------- helpers
RUN_ENVELOPE_KEYS = {
    "run_id", "report_id", "status", "api_version",
    "created_at", "completed_at", "duration_ms", "client", "requested_by", "tenant_id",
}


def report_body(obj: dict) -> dict:
    """Return the Report JSON body, and prove it is not a Run envelope.

    `report = f(snapshot, params, pipeline_version)` is only comparable if the
    thing being compared is the report. The Run envelope is wall-clock and
    per-execution by design (API_BOUNDARY_V1 section 3.1): `run_id`,
    `created_at` and `duration_ms` SHOULD differ between two identical runs.
    Comparing a full `/api/v1/runs` response would therefore fail for a correct
    implementation — so this guard is an assertion, not a comment, and it fires
    if `run_report()` is ever changed to return the envelope.
    """
    body = obj.get("report") if "report" in obj and "run" in obj else obj
    assert "schema_version" in body, "not a Report JSON body"
    leaked = RUN_ENVELOPE_KEYS & set(body)
    assert not leaked, f"Run-envelope fields leaked into the report body: {sorted(leaked)}"
    return body


def _relation(report: dict, source: str) -> dict:
    for rel in report["relations"]:
        if rel["source"] == source:
            return rel
    raise AssertionError(f"{source!r} missing from relations[] — every candidate must appear")


def _run(name: str) -> dict:
    f = MANIFEST["fixtures"][name]
    return report_body(run_report(FIXTURES / f["file"], f["request"]))


@pytest.fixture(scope="module")
def positive() -> dict:
    return _run("s_gt_1_positive")


@pytest.fixture(scope="module")
def negative() -> dict:
    return _run("s_gt_2_negative")


# ------------------------------------------------------- S-GT-0  integrity
@pytest.mark.parametrize("name", ["s_gt_1_positive", "s_gt_2_negative"])
def test_sgt0_fixture_integrity(name: str) -> None:
    """The ground truth must not move without someone noticing.

    If this fails, a fixture was regenerated. Regenerating is allowed; doing it
    without re-recording the manifest is not, because every threshold decision
    downstream is calibrated against these exact files.
    """
    f = MANIFEST["fixtures"][name]
    digest = hashlib.sha256((FIXTURES / f["file"]).read_bytes()).hexdigest()
    assert digest == f["sha256"], f"{f['file']} changed; regenerate the manifest deliberately"


# -------------------------------------------------- S-GT-1  positive control
def test_sgt1_injected_relation_is_selected(positive: dict) -> None:
    assert positive["outcome"] == "ok"
    assert positive["selection"]["fit_status"] == "fit"
    assert positive["selection"]["selected_count"] >= 1
    assert "true_driver" in positive["selection"]["selected_sources"]


def test_sgt1_recovers_lag_and_sign(positive: dict) -> None:
    """Detecting *a* relation is not enough — it must be the right one.

    Sign is asserted because sign bugs are silent: a detector that reports the
    correct magnitude with an inverted sign passes every strength check and
    tells the user the opposite of the truth.
    """
    rel = _relation(positive, "true_driver")
    assert rel["selected"] is True
    assert rel["reason_code"] == "selected"
    assert rel["lag"] == SPEC["injected_lag"]
    assert rel["effect"]["sign"] == -1
    assert rel["transform"] == "diff"


def test_sgt1_effect_clears_noise_floor_and_fdr(positive: dict) -> None:
    rel = _relation(positive, "true_driver")
    assert rel["effect"]["score"] > rel["effect"]["noise_floor"]
    assert rel["effect"]["effect_size_vs_noise_floor"] > 1.0
    assert rel["significance"]["clears"] is True
    assert rel["stability"] is not None, "a selected relation cannot have unknown stability"


def test_sgt1_decoys_are_rejected(positive: dict) -> None:
    """The positive control doubles as a false-positive check: the same run must
    reject three independent decoys, which is what exercises FDR correction."""
    for name in ("decoy_1", "decoy_2", "decoy_3"):
        rel = _relation(positive, name)
        assert rel["selected"] is False, f"{name} was selected — spurious relation accepted"
        assert rel["reason_code"] in REJECTION_CODES


def test_sgt1_persistent_levels_accepted_under_diff(positive: dict) -> None:
    """Fixture levels are integrated (lag-1 ACF ~0.98). Declaring `diff` must be
    accepted; this is the S7 guard passing rather than firing."""
    for d in positive.get("transform_diagnostics") or []:
        assert d["verdict"] == "accepted", d


# -------------------------------------------------- S-GT-2  negative control
def test_sgt2_pure_noise_yields_baseline_only(negative: dict) -> None:
    assert negative["outcome"] == "baseline_only"
    assert negative["selection"]["fit_status"] == "baseline_only_no_evidence"
    assert negative["selection"]["selected_count"] == 0
    assert negative["selection"]["selected_sources"] == []


def test_sgt2_every_candidate_still_reported(negative: dict) -> None:
    """`relations[]` carries EVERY candidate, selected or not (W0 section 3).

    This catches the tempting bug where "nothing was selected" is implemented as
    an empty array — which would silently strip the evidence panel that explains
    *why* each candidate was rejected. That panel is the product.
    """
    expected = MANIFEST["fixtures"]["s_gt_2_negative"]["request"]["candidate_signals"]
    assert len(negative["relations"]) == len(expected)
    for rel in negative["relations"]:
        assert rel["selected"] is False
        assert rel["reason_code"] in REJECTION_CODES
        assert rel.get("reason_text"), "a rejection with no explanation is not a result"


def test_sgt2_baseline_and_narrative_present(negative: dict) -> None:
    """baseline_only is a success state, so it must arrive fully furnished."""
    assert negative["baseline"]["name"]
    assert isinstance(negative["baseline"]["mae"], (int, float))
    assert negative["narrative"]["headline"]


def test_sgt2_null_is_not_zero(negative: dict) -> None:
    """Null means "insufficient evidence" and must never be coerced to 0 — the
    UI renders those two states differently on purpose (W0 section 8).

    With nothing selected there is no basis for a confidence number, so the
    honest emission is null. A 0.0 here would render as "zero confidence",
    which is a claim; null renders as "unknown", which is the truth.
    """
    pc = negative.get("prediction_confidence")
    if pc is not None:
        assert pc.get("confidence") is None, (
            "no relation was selected, so confidence is unknown (null), not 0"
        )
    for rel in negative["relations"]:
        for field in ("stability", "uncertainty"):
            value = rel.get(field)
            assert value is None or isinstance(value, (int, float)), field


# ------------------------------------------- S-GT-2b  false-positive rate
@pytest.mark.slow
def test_sgt2b_false_positive_rate_across_seeds() -> None:
    """Statistical version of the negative control.

    The CI control uses one screened seed so it is deterministic. That cannot
    measure the false-positive RATE, which is what actually says whether the
    gate is calibrated. Run this nightly, not per-commit.
    """
    import sys  # noqa: PLC0415

    sys.path.insert(0, str(Path(__file__).parent))
    from generate_ground_truth import build_negative, request_payload  # noqa: PLC0415

    import tempfile  # noqa: PLC0415

    n_trials, false_positives = 20, 0
    for seed in range(30000, 30000 + n_trials):
        df = build_negative(seed)
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as fh:
            df.to_csv(fh.name, index=False)
            report = report_body(run_report(Path(fh.name), request_payload(df, "synthetic_target")))
        if report["selection"]["selected_count"] > 0:
            false_positives += 1

    rate = false_positives / n_trials
    assert rate <= 0.10, (
        f"false-positive rate {rate:.0%} over {n_trials} pure-noise datasets. "
        "The gate is admitting spurious relations."
    )


# ----------------------------------------------------- S-GT-3  determinism
def test_sgt3_report_is_reproducible() -> None:
    """report = f(snapshot, params, pipeline_version) — API_BOUNDARY_V1 P2.

    Same input, byte-identical report. This is the claim that makes
    `snapshot.hash` mean anything; if it fails, nothing else in the product's
    credibility story survives. Run-envelope fields are excluded because they are
    wall-clock by design and live outside the report (API_BOUNDARY_V1 section 3.1).
    """
    a, b = _run("s_gt_1_positive"), _run("s_gt_1_positive")
    dump = lambda r: json.dumps(r, sort_keys=True, separators=(",", ":"))  # noqa: E731
    assert dump(a) == dump(b), "identical input produced two different reports"
