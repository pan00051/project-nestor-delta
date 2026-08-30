"""Keep the published Evidence Gate configuration aligned with core defaults."""

from __future__ import annotations

from inspect import signature

import pytest

from nestor_delta.evidence_gate import select_relations_with_evidence
from nestor_delta_service.adapter import EVIDENCE_GATE_CONFIG


GATE_KEYS = (
    "alpha",
    "min_stability",
    "max_uncertainty",
    "min_sample_support",
)


def _core_gate_defaults() -> dict[str, float]:
    parameters = signature(select_relations_with_evidence).parameters
    return {key: parameters[key].default for key in GATE_KEYS}


def _assert_gate_config_matches(config: dict[str, float]) -> None:
    assert config == _core_gate_defaults()


def test_adapter_gate_config_matches_core_defaults() -> None:
    _assert_gate_config_matches(EVIDENCE_GATE_CONFIG)


def test_gate_config_guard_rejects_in_memory_mismatch() -> None:
    mismatched = dict(EVIDENCE_GATE_CONFIG)
    mismatched["min_stability"] += 0.01

    with pytest.raises(AssertionError):
        _assert_gate_config_matches(mismatched)
