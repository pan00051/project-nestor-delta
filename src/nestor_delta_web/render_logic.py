"""Pure, Streamlit-free rendering decisions for the Delta website.

Every function here takes plain dicts (an API response, or a piece of one) and
returns display decisions. No Streamlit, no `nestor_delta` import, no analytic
recomputation. This is the layer the contract/state tests exercise against
`docs/mock_reports_v1.json` without a live backend.

Two rules are encoded structurally, because they are the product:
  1. A null value is shown as "insufficient / not evaluated", never as 0.
  2. baseline_only, and every error class, are distinct states — never "No data".
"""

from __future__ import annotations

from typing import Any, Mapping, Optional

SCHEMA_VERSION = "delta.report.v1"

# transport-level pseudo states produced by the api client (no HTTP body)
TRANSPORT_STATES = {"unreachable", "timeout"}

# outcome -> internal view id
_OUTCOME_VIEW = {
    "ok": "report_ok",
    "baseline_only": "report_baseline",
    "ok_to_analyze": "audit_ok",
    "snapshot_ready": "snapshot_ready",
    "validation_error": "validation_error",
    "not_found": "not_found",
    "analysis_failure": "analysis_failure",
}

# distinct, human states — the UI must render each differently.
ERROR_VIEWS = {"validation_error", "not_found", "analysis_failure",
               "unreachable", "timeout", "malformed"}

EVIDENCE_GATE_EXPLANATION = (
    "FDR, stability, uncertainty, and sample support decide which candidate "
    "relations enter this run."
)
BASELINE_SUCCESS_STATEMENT = (
    "This is intended behavior: Delta keeps the baseline instead of adding "
    "unsupported relationships."
)
P0_ANSWER_ORDER = (
    "run_status",
    "gate_result",
    "selection",
    "relation_evidence",
    "gate_reasons",
)


def classify_response(
    status: Optional[int],
    body: Optional[Mapping[str, Any]],
    transport: Optional[str] = None,
) -> str:
    """Map an API result to exactly one view id.

    `transport` is set by the client when there is no valid HTTP body at all
    (connection refused, timeout, non-JSON). It wins over everything.
    """
    if transport in TRANSPORT_STATES:
        return transport
    if not isinstance(body, Mapping):
        return "malformed"
    if body.get("schema_version") != SCHEMA_VERSION:
        return "malformed"
    outcome = body.get("outcome")
    if outcome not in _OUTCOME_VIEW:
        return "malformed"
    return _OUTCOME_VIEW[outcome]


def is_error_view(view: str) -> bool:
    return view in ERROR_VIEWS


# ---------------------------------------------------------------- values

_NULL_TEXT = "insufficient / not evaluated"


def is_null(value: Any) -> bool:
    return value is None


def fmt_number(value: Any, digits: int = 3) -> str:
    """A number, or an em dash for null. Never coerces null to 0."""
    if value is None:
        return "—"
    return f"{float(value):.{digits}f}"


def fmt_p_value(value: Any) -> str:
    """A p-value display string. Tiny non-zero values are not rounded to 0."""
    if value is None:
        return "—"
    number = float(value)
    if number == 0.0:
        return "< 1e-12"
    if 0.0 < number < 1e-12:
        return "< 1e-12"
    if 0.0 < number < 0.0001:
        return f"{number:.1e}"
    return f"{number:.4f}"


def fmt_percent(value: Any, digits: int = 1) -> str:
    if value is None:
        return "—"
    return f"{float(value) * 100:+.{digits}f}%"


def fmt_signed(value: Any, digits: int = 3) -> str:
    if value is None:
        return "—"
    return f"{float(value):+.{digits}f}"


def confidence_display(report: Mapping[str, Any]) -> dict[str, Any]:
    """Prediction confidence for display. Null stays null, never 0."""
    pc = report.get("prediction_confidence")
    if not isinstance(pc, Mapping) or pc.get("confidence") is None:
        return {"is_null": True, "text": _NULL_TEXT, "value": None,
                "capped_by": (pc or {}).get("capped_by")}
    return {"is_null": False, "text": f"{float(pc['confidence']) * 100:.0f}%",
            "value": float(pc["confidence"]), "capped_by": pc.get("capped_by")}


def report_decision(report: Mapping[str, Any]) -> dict[str, Any]:
    """User-facing decision header derived only from report outcome and narrative."""
    outcome = report.get("outcome")
    narrative = report.get("narrative") or {}
    selection = report.get("selection") or {}
    confidence = confidence_display(report)
    if outcome == "baseline_only":
        default_headline = "No relationship cleared the evidence gate"
        default_summary = (
            "Delta completed the analysis and kept the persistence baseline. "
            "This is a valid result, not missing data."
        )
        tone = "baseline"
    else:
        default_headline = "Analysis complete"
        default_summary = (
            "Delta completed the analysis and selected the relations shown below."
        )
        tone = "selected"
    lines = narrative.get("lines") if isinstance(narrative, Mapping) else []
    selected_count = selection.get("selected_count")
    candidate_signals = (report.get("case") or {}).get("candidate_signals")
    candidate_count = (
        len(candidate_signals)
        if isinstance(candidate_signals, list)
        else len(report.get("relations") or [])
    )
    rejected_count = (
        candidate_count - selected_count
        if isinstance(selected_count, int) and candidate_count >= selected_count
        else None
    )
    return {
        "tone": tone,
        "run_status": "Analysis completed successfully",
        "headline": narrative.get("headline") or default_headline,
        "summary": lines[0] if isinstance(lines, list) and lines else default_summary,
        "lines": lines if isinstance(lines, list) else [],
        "gate_explanation": EVIDENCE_GATE_EXPLANATION,
        "success_statement": (
            BASELINE_SUCCESS_STATEMENT if outcome == "baseline_only" else None
        ),
        "candidate_count": candidate_count,
        "selected_count": selected_count,
        "rejected_count": rejected_count,
        "fit_status": selection.get("fit_status"),
        "final_mode": selection.get("final_mode"),
        "confidence": confidence,
    }


def report_context(report: Mapping[str, Any]) -> dict[str, Any]:
    case = report.get("case") or {}
    snapshot = report.get("snapshot") or {}
    return {
        "case_name": case.get("name"),
        "target": case.get("target"),
        "frequency": case.get("frequency"),
        "observations": case.get("n_observations"),
        "train_end": case.get("train_end"),
        "lag_window": case.get("lag_window"),
        "generated_as_of": report.get("generated_as_of"),
        "snapshot_hash": snapshot.get("hash"),
        "snapshot_source": snapshot.get("source"),
        "pipeline_version": report.get("pipeline_version"),
    }


def context_bar_items(report: Mapping[str, Any]) -> list[dict[str, Any]]:
    """P1 provenance anchors, in their required display order."""
    context = report_context(report)
    return [
        {"label": "Case", "value": context["case_name"]},
        {"label": "As of", "value": context["generated_as_of"]},
        {"label": "Snapshot", "value": context["snapshot_hash"]},
        {"label": "Pipeline", "value": context["pipeline_version"]},
    ]


def report_filename(report: Mapping[str, Any]) -> str:
    context = report_context(report)
    raw = str(context.get("case_name") or context.get("target") or "analysis")
    safe = "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in raw)
    safe = safe.strip("-") or "analysis"
    return f"nestor-delta-{safe}.json"


# ---------------------------------------------------------------- charts / guards

def should_show_evaluation(report: Mapping[str, Any]) -> bool:
    """True only when a real rolling-origin interval exists. No fake intervals."""
    ev = report.get("evaluation")
    if not isinstance(ev, Mapping):
        return False
    ro = ev.get("rolling_origin")
    return isinstance(ro, Mapping) and ro.get("median") is not None


def evaluation_interval(report: Mapping[str, Any]) -> Optional[dict[str, Any]]:
    if not should_show_evaluation(report):
        return None
    ro = report["evaluation"]["rolling_origin"]
    return {"median": ro.get("median"), "low": ro.get("low"), "high": ro.get("high"),
            "folds": ro.get("folds"), "resolves": bool(ro.get("resolves"))}


def should_show_trajectory(relation: Mapping[str, Any]) -> bool:
    """True only when trajectory is a non-empty list. null or [] -> no timeline."""
    traj = relation.get("trajectory")
    return isinstance(traj, list) and len(traj) > 0


# ---------------------------------------------------------------- lifecycle

_LIFECYCLE = {
    "insufficient_evidence": ("Insufficient evidence", "neutral"),
    "birth": ("Birth", "neutral"),
    "strengthening": ("Strengthening", "good"),
    "stable": ("Stable", "good"),
    "decaying": ("Decaying", "warn"),   # a detected fact, not an alarm
    "dead": ("Dead", "muted"),
}


def lifecycle_badge(state: Any) -> dict[str, str]:
    """Raw lifecycle state -> label + tone. Never invents a state."""
    label, tone = _LIFECYCLE.get(state, (str(state), "neutral"))
    return {"state": str(state), "label": label, "tone": tone}


def lifecycle_steps(state: Any) -> list[dict[str, Any]]:
    """Return the canonical lifecycle order with the reported state highlighted."""
    return [
        {"state": key, "label": label, "active": key == state}
        for key, (label, _tone) in _LIFECYCLE.items()
    ]


# ---------------------------------------------------------------- relations

_REASON_TEXT = {
    "selected": "Cleared effect, stability, support, and FDR.",
    "below_fdr_corrected_effect": "Effect does not survive multiple-comparison (FDR) correction.",
    "insufficient_stability": "Stability is below the selection requirement across rolling windows.",
    "excess_relationship_uncertainty": "Estimate too uncertain to trust.",
    "insufficient_sample_support": "Too little sample support.",
    "not_selected": "Not selected.",
}


def reason_text(code: Any) -> str:
    return _REASON_TEXT.get(code, str(code))


def direction_label(sign: Any) -> str:
    if sign is None:
        return "—"
    number = float(sign)
    if number > 0:
        return "positive"
    if number < 0:
        return "negative"
    return "neutral"


def relation_view(relation: Mapping[str, Any]) -> dict[str, Any]:
    """Flatten one RelationView into display fields. No recomputation."""
    effect = relation.get("effect") or {}
    sig = relation.get("significance") or {}
    return {
        "source": relation.get("source"),
        "target": relation.get("target"),
        "lag": relation.get("lag"),
        "transform": relation.get("transform"),
        "score": effect.get("score"),
        "weight": effect.get("weight"),
        "sign": effect.get("sign"),
        "direction": direction_label(effect.get("sign")),
        "noise_floor": effect.get("noise_floor"),
        "effect_size": effect.get("effect_size_vs_noise_floor"),
        "p_value": sig.get("p_value"),
        "fdr_threshold": sig.get("fdr_threshold"),
        "clears_fdr": sig.get("clears"),
        "stability": relation.get("stability"),
        "uncertainty": relation.get("uncertainty"),
        "sample_support": relation.get("sample_support"),
        "lifecycle": lifecycle_badge((relation.get("lifecycle") or {}).get("state")),
        "selected": relation.get("selected"),
        "reason_code": relation.get("reason_code"),
        "reason_text": relation.get("reason_text") or reason_text(relation.get("reason_code")),
        "has_trajectory": should_show_trajectory(relation),
    }


def relation_views(report: Mapping[str, Any]) -> list[dict[str, Any]]:
    return [relation_view(r) for r in report.get("relations", [])]


def report_p0_answers(report: Mapping[str, Any]) -> dict[str, Any]:
    """The accepted result-page answer hierarchy, in P0 display order."""
    decision = report_decision(report)
    views = relation_views(report)
    return {
        "run_status": decision["run_status"],
        "gate_result": {
            "headline": decision["headline"],
            "explanation": decision["gate_explanation"],
            "success_statement": decision["success_statement"],
        },
        "selection": {
            "candidate_count": decision["candidate_count"],
            "selected_count": decision["selected_count"],
            "rejected_count": decision["rejected_count"],
        },
        "relation_evidence": views,
        "gate_reasons": [
            {
                "relation": f"{view['source']} → {view['target']}",
                "reason_code": view["reason_code"],
                "reason_text": view["reason_text"],
            }
            for view in views
        ],
    }


def relation_expander_label(view: Mapping[str, Any]) -> str:
    """Collapsed relation label. Lifecycle is paired with stability per F.2."""
    selection = "insufficient" if view["selected"] is None else (
        "selected" if view["selected"] else "not selected"
    )
    lifecycle = (view.get("lifecycle") or {}).get("label")
    return (
        f"{view['source']} → {view['target']} · "
        f"{view['direction']} · lag {view['lag']} · score {fmt_number(view['score'])} · "
        f"{lifecycle} / stability {fmt_number(view.get('stability'))} · {selection}"
    )


ANALYST_TABLE_COLUMNS = (
    "selected",
    "relation",
    "lag",
    "transform",
    "weight",
    "score",
    "stability",
    "uncertainty",
    "sample support",
    "lifecycle",
    "reason",
    "noise floor (diagnostic)",
)


def analyst_table_rows(report: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for view in relation_views(report):
        rows.append(
            {
                "selected": (
                    "—"
                    if view["selected"] is None
                    else ("yes" if view["selected"] else "no")
                ),
                "relation": f"{view['source']} → {view['target']}",
                "lag": view["lag"],
                "transform": view["transform"],
                "weight": fmt_signed(view["weight"]),
                "score": fmt_number(view["score"]),
                "stability": fmt_number(view["stability"]),
                "uncertainty": fmt_number(view["uncertainty"]),
                "sample support": fmt_number(view["sample_support"]),
                "lifecycle": view["lifecycle"]["label"],
                "reason": view["reason_code"],
                "noise floor (diagnostic)": fmt_number(view["noise_floor"]),
            }
        )
    return rows


def _fmt_plain(value: Any) -> str:
    if value is None:
        return "—"
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, float):
        return f"{value:g}"
    if isinstance(value, list):
        return ", ".join(map(str, value)) if value else "—"
    if isinstance(value, Mapping):
        if not value:
            return "—"
        return ", ".join(f"{key}={value[key]}" for key in sorted(value))
    return str(value)


def configuration_rows(report: Mapping[str, Any]) -> list[dict[str, str]]:
    """Effective configuration rows for display. Missing old-report blocks stay quiet."""
    config = report.get("configuration")
    if not isinstance(config, Mapping):
        return []

    inputs = config.get("inputs") or {}
    effect = config.get("effect") or {}
    rolling = config.get("rolling_lifecycle") or {}
    noise = config.get("noise_floor") or {}
    gate = config.get("evidence_gate") or {}
    reproducibility = config.get("reproducibility") or {}

    rows = [
        ("Inputs", "Source", inputs.get("source")),
        ("Inputs", "Training cutoff", inputs.get("train_end")),
        ("Inputs", "Lag window", inputs.get("lag_window")),
        ("Inputs", "Candidate count", inputs.get("candidate_count")),
        ("Inputs", "Training observations", inputs.get("train_observations")),
        ("Inputs", "Transform declarations", inputs.get("transform_declarations")),
        ("Effect", "Score scope", effect.get("score_scope")),
        ("Effect", "Ranking", effect.get("ranking")),
        ("Rolling lifecycle", "Window rule", rolling.get("window_rule")),
        ("Rolling lifecycle", "Effective window", rolling.get("effective_window")),
        ("Rolling lifecycle", "Step interval", rolling.get("step_interval")),
        ("Rolling lifecycle", "State rule", rolling.get("state_rule")),
        ("Noise floor", "Role", noise.get("role")),
        ("Noise floor", "Comparisons rule", noise.get("comparisons_rule")),
        ("Noise floor", "Comparisons", noise.get("comparisons")),
        ("Noise floor", "Alpha", noise.get("alpha")),
        ("Evidence gate", "Selection terms", gate.get("selection_terms")),
        ("Evidence gate", "Alpha", gate.get("alpha")),
        ("Evidence gate", "Minimum stability", gate.get("min_stability")),
        ("Evidence gate", "Maximum uncertainty", gate.get("max_uncertainty")),
        ("Evidence gate", "Minimum sample support", gate.get("min_sample_support")),
        ("Reproducibility", "Rule", reproducibility.get("rule")),
    ]
    return [
        {"section": section, "setting": setting, "value": _fmt_plain(value)}
        for section, setting, value in rows
        if value is not None
    ]


# ---------------------------------------------------------------- audit + transforms

def transform_conflicts(diagnostics: Any) -> list[str]:
    """Signals that block analysis: rejected verdict (persistent + declared none)."""
    if not isinstance(diagnostics, list):
        return []
    return [d.get("signal") for d in diagnostics if d.get("verdict") == "rejected"]


def analyze_allowed(diagnostics: Any) -> bool:
    """Analyze is allowed only when no declaration is rejected."""
    return len(transform_conflicts(diagnostics)) == 0


def audit_signal_rows(data_audit: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for s in (data_audit or {}).get("signals", []):
        cov = s.get("coverage") or {}
        rows.append({
            "signal": s.get("signal"),
            "sample_count": s.get("sample_count"),
            "unit": s.get("unit"),
            "seasonal_adjustment": s.get("seasonal_adjustment"),
            "coverage": f"{cov.get('start')}…{cov.get('end')}" if cov else "—",
            "lag1_acf": s.get("lag1_acf"),
            "persistent": bool(s.get("highly_persistent_risk")),
        })
    return rows


def date_axis_summary(data_audit: Mapping[str, Any]) -> dict[str, Any]:
    da = (data_audit or {}).get("date_axis", {}) or {}
    return {
        "continuous": bool(da.get("continuous")),
        "expected": da.get("expected_months"),
        "present": da.get("present"),
        "missing": da.get("missing_months", []) or [],
        "duplicates": da.get("duplicate_months", []) or [],
    }


# ---------------------------------------------------------------- errors + snapshot

def error_display(body: Mapping[str, Any]) -> dict[str, Any]:
    err = (body or {}).get("error") or {}
    return {"code": err.get("code"), "message": err.get("message"),
            "field": err.get("field"), "detail": err.get("detail")}


def snapshot_summary(body: Mapping[str, Any]) -> dict[str, Any]:
    snap = (body or {}).get("snapshot") or {}
    return {"hash": snap.get("hash"), "source": snap.get("source"),
            "provenance": snap.get("provenance"),
            "row_count": body.get("row_count"), "columns": body.get("columns"),
            "has_csv": bool(body.get("csv_base64"))}


def frozen_snapshot_payload(
    snapshot_body: Mapping[str, Any],
    source_payload: Mapping[str, Any],
) -> dict[str, Any]:
    """Turn a snapshot response into the immutable upload payload used downstream."""
    csv_base64 = snapshot_body.get("csv_base64")
    columns = snapshot_body.get("columns") or []
    if not csv_base64 or not columns:
        raise ValueError("snapshot response must include csv_base64 and columns")
    return {
        "csv_base64": csv_base64,
        "date_column": columns[0],
        "target": source_payload.get("target"),
        "candidate_signals": list(source_payload.get("candidate_signals") or []),
        "transform_declarations": dict(
            source_payload.get("transform_declarations") or {}
        ),
        "train_end": source_payload.get("train_end"),
        "lag_window": source_payload.get("lag_window"),
    }
