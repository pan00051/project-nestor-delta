"""Pin the exact files covered by Report pipeline_version."""

from __future__ import annotations

from pathlib import Path

from nestor_delta_service import versioning


REPO = Path(__file__).resolve().parents[1]

EXPECTED_PIPELINE_PATHS = (
    "src/nestor_delta_service/versioning.py",
    "src/nestor_delta_service/adapter.py",
    "src/nestor_delta/__init__.py",
    "src/nestor_delta/baselines.py",
    "src/nestor_delta/config.py",
    "src/nestor_delta/dynamic_prediction.py",
    "src/nestor_delta/dynamic_weights.py",
    "src/nestor_delta/evidence_gate.py",
    "src/nestor_delta/frozen_adaptive_test.py",
    "src/nestor_delta/interval_metrics.py",
    "src/nestor_delta/metrics.py",
    "src/nestor_delta/noise_floor.py",
    "src/nestor_delta/prediction_confidence.py",
    "src/nestor_delta/real_budget_sweep.py",
    "src/nestor_delta/real_case_analysis.py",
    "src/nestor_delta/real_data.py",
    "src/nestor_delta/relation_weights.py",
    "src/nestor_delta/reporting.py",
    "src/nestor_delta/resource_adaptive_ignore.py",
    "src/nestor_delta/resource_adaptive_prediction.py",
    "src/nestor_delta/rolling_origin.py",
    "src/nestor_delta/s10_fixtures.py",
    "src/nestor_delta/s4_config.py",
    "src/nestor_delta/s5_config.py",
    "src/nestor_delta/s7_fixtures.py",
    "src/nestor_delta/s9_fixtures.py",
    "src/nestor_delta/splits.py",
    "src/nestor_delta/stage1_prediction.py",
    "src/nestor_delta/stationarity.py",
    "src/nestor_delta/synthetic.py",
    "src/nestor_delta/synthetic_drift.py",
    "src/nestor_delta/synthetic_resource_stress.py",
    "src/nestor_delta/temporal_stability.py",
    "src/nestor_delta/trust_gated_prediction.py",
    "src/nestor_delta/trust_gating.py",
    "src/nestor_delta/validation_parameter_search.py",
)


def test_pipeline_version_hash_scope_is_explicit(monkeypatch) -> None:
    original_read_bytes = Path.read_bytes
    observed: list[str] = []

    def recording_read_bytes(path: Path) -> bytes:
        relative = path.relative_to(REPO).as_posix()
        if relative.startswith("src/"):
            observed.append(relative)
        return original_read_bytes(path)

    monkeypatch.setattr(Path, "read_bytes", recording_read_bytes)

    versioning.pipeline_version()

    assert tuple(observed) == EXPECTED_PIPELINE_PATHS
