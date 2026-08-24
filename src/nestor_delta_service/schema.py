"""Executable Report JSON v1 schema artifact."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict


class FlexibleModel(BaseModel):
    model_config = ConfigDict(extra="allow")


class ErrorBody(FlexibleModel):
    code: str
    message: str
    field: Optional[str] = None
    detail: Optional[Dict[str, Any]] = None


class Snapshot(FlexibleModel):
    hash: Optional[str] = None
    source: Optional[str] = None
    provenance: Optional[Dict[str, Any]] = None


class Case(FlexibleModel):
    name: Optional[str] = None
    target: Optional[str] = None
    candidate_signals: Optional[List[str]] = None
    frequency: Optional[str] = None
    n_observations: Optional[int] = None
    train_end: Optional[str] = None
    lag_window: Optional[int] = None


class Effect(FlexibleModel):
    score: Optional[float] = None
    weight: Optional[float] = None
    sign: Optional[int] = None
    noise_floor: Optional[float] = None
    effect_size_vs_noise_floor: Optional[float] = None


class Significance(FlexibleModel):
    p_value: Optional[float] = None
    fdr_threshold: Optional[float] = None
    clears: Optional[bool] = None


class Lifecycle(FlexibleModel):
    state: Optional[str] = None
    points: Optional[int] = None


class RelationView(FlexibleModel):
    source: Optional[str] = None
    target: Optional[str] = None
    lag: Optional[int] = None
    transform: Optional[str] = None
    effect: Optional[Effect] = None
    significance: Optional[Significance] = None
    stability: Optional[float] = None
    uncertainty: Optional[float] = None
    sample_support: Optional[float] = None
    lifecycle: Optional[Lifecycle] = None
    selected: Optional[bool] = None
    reason_code: Optional[str] = None
    reason_text: Optional[str] = None
    trajectory: Optional[List[Dict[str, Any]]] = None


class Selection(FlexibleModel):
    fit_status: Optional[str] = None
    final_mode: Optional[str] = None
    selected_count: Optional[int] = None
    selected_sources: Optional[List[str]] = None


class Baseline(FlexibleModel):
    name: Optional[str] = None
    mae: Optional[float] = None


class Narrative(FlexibleModel):
    headline: Optional[str] = None
    lines: Optional[List[str]] = None


class PredictionConfidence(FlexibleModel):
    confidence: Optional[float] = None
    components: Optional[Dict[str, Any]] = None
    capped_by: Optional[str] = None


class ReportJsonV1(FlexibleModel):
    schema_version: str
    producer: Optional[str] = None
    pipeline_version: Optional[str] = None
    outcome: str
    generated_as_of: Optional[str] = None
    case: Optional[Case] = None
    snapshot: Optional[Snapshot] = None
    configuration: Optional[Dict[str, Any]] = None
    transform_declarations: Optional[Dict[str, str]] = None
    transform_diagnostics: Optional[List[Dict[str, Any]]] = None
    data_audit: Optional[Dict[str, Any]] = None
    baseline: Optional[Baseline] = None
    evaluation: Optional[Dict[str, Any]] = None
    noise_floor: Optional[Dict[str, Any]] = None
    relations: Optional[List[RelationView]] = None
    selection: Optional[Selection] = None
    prediction_confidence: Optional[PredictionConfidence] = None
    narrative: Optional[Narrative] = None
    warnings: Optional[List[Any]] = None
    error: Optional[ErrorBody] = None


def report_json_schema() -> dict[str, Any]:
    return ReportJsonV1.model_json_schema()
