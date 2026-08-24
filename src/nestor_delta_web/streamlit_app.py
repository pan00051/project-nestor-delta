"""Nestor Delta user-facing Streamlit frontend.

The frontend talks to the FastAPI adapter over HTTP and renders Report JSON v1.
It never imports `nestor_delta` or recomputes an analytic conclusion.
"""

from __future__ import annotations

import base64
import html
import json
from typing import Any, Mapping

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from nestor_delta_web import api_client as api
from nestor_delta_web import presets
from nestor_delta_web import render_logic as rl

st.set_page_config(
    page_title="Nestor Delta — Relationship Reliability",
    page_icon="◐",
    layout="wide",
)

_CSS = """
<style>
:root{
  --delta-bg:#f4f4f1;--delta-surface:#fcfcfb;--delta-soft:#eeeee9;
  --delta-ink:#11110f;--delta-muted:#66645f;--delta-faint:#8b8982;
  --delta-line:#dcdad3;--delta-accent:#1769c2;--delta-good:#1f7438;
  --delta-warn:#9a6800;--delta-serious:#b44924;
  --delta-sidebar:#eaeae5;--delta-primary-ink:#fcfcfb;
  color-scheme:light dark;
}
[data-testid="stAppViewContainer"], [data-testid="stHeader"]{background:var(--delta-bg)}
[data-testid="stMainBlockContainer"]{max-width:1040px;padding-top:2rem;padding-bottom:5rem}
[data-testid="stSidebar"]{background:var(--delta-sidebar);border-right:1px solid var(--delta-line)}
[data-testid="stAppViewContainer"]{overflow-x:hidden}
h1,h2,h3,p,div{letter-spacing:0}
h1{font-size:2.15rem!important;line-height:1.12!important;margin-bottom:.45rem!important}
h2{font-size:1.25rem!important;margin-top:2.25rem!important}
h3{font-size:1rem!important}
.delta-brandline{display:flex;flex-wrap:nowrap;gap:.35rem;max-width:100%;overflow:visible;white-space:normal;font-size:.76rem;line-height:1.35;letter-spacing:.08em;text-transform:uppercase;color:var(--delta-faint);font-weight:650}
.delta-brandline span{flex-shrink:0;white-space:nowrap}
.delta-lede{max-width:760px;color:var(--delta-muted);font-size:.95rem;line-height:1.6;margin-bottom:1.4rem}
.delta-scroll-anchor{display:block;position:relative;top:-.9rem;width:1px;height:1px;overflow:hidden}
.delta-section{border-top:1px solid var(--delta-line);padding-top:1.1rem;margin-top:1.8rem}
.delta-section-kicker{font-size:.72rem;letter-spacing:.08em;text-transform:uppercase;color:var(--delta-faint);font-weight:700}
.delta-section-title{font-size:1.1rem;font-weight:700;color:var(--delta-ink);margin:.15rem 0 .2rem}
.delta-section-copy{font-size:.86rem;color:var(--delta-muted);max-width:760px}
.delta-steps{display:grid;grid-template-columns:repeat(3,1fr);border-top:1px solid var(--delta-line);border-bottom:1px solid var(--delta-line);margin:1.25rem 0 1.6rem}
.delta-step{padding:.72rem .8rem;color:var(--delta-faint);font-size:.78rem;border-right:1px solid var(--delta-line)}
.delta-step:last-child{border-right:0}.delta-step b{display:block;color:inherit;font-size:.68rem;text-transform:uppercase;letter-spacing:.06em;margin-bottom:.12rem}
.delta-step.active{color:var(--delta-accent);background:rgba(23,105,194,.055)}
.delta-step.done{color:var(--delta-muted)}
.delta-decision{border-left:4px solid var(--delta-accent);padding:1.05rem 1.2rem;background:var(--delta-surface);margin:.8rem 0 1.3rem}
.delta-decision.baseline{border-left-color:var(--delta-warn)}
.delta-decision.selected{border-left-color:var(--delta-good)}
.delta-decision .eyebrow{font-size:.7rem;text-transform:uppercase;letter-spacing:.08em;color:var(--delta-faint);font-weight:700}
.delta-decision .headline{font-size:1.35rem;line-height:1.25;font-weight:720;margin:.25rem 0;color:var(--delta-ink)}
.delta-decision .summary{font-size:.9rem;line-height:1.55;color:var(--delta-muted);max-width:800px}
.delta-context{font-size:.78rem;color:var(--delta-muted);padding:.55rem 0;border-bottom:1px solid var(--delta-line);overflow-wrap:anywhere}
.delta-status{display:inline-flex;align-items:center;border:1px solid var(--delta-line);border-radius:999px;padding:.16rem .55rem;font-size:.72rem;font-weight:650;color:var(--delta-muted)}
.delta-status.good{color:var(--delta-good);border-color:#a9c9b2;background:#eef6ef}
.delta-status.warn{color:var(--delta-warn);border-color:#dbc99a;background:#fbf5e5}
.delta-status.serious{color:var(--delta-serious);border-color:#dfb39f;background:#fbede7}
.delta-status.muted{color:var(--delta-faint)}
.delta-relation{border-top:1px solid var(--delta-line);padding:.9rem 0 .25rem;margin-top:.45rem}
.delta-relation-head{display:flex;align-items:flex-start;justify-content:space-between;gap:1rem}
.delta-relation-name{font-weight:700;font-size:1rem;overflow-wrap:anywhere}.delta-relation-meta{font-size:.78rem;color:var(--delta-muted);margin-top:.16rem}
.delta-life{display:grid;grid-template-columns:repeat(5,1fr);gap:4px;margin:.8rem 0}
.delta-life span{border-top:3px solid var(--delta-line);padding-top:.3rem;font-size:.66rem;color:var(--delta-faint);text-align:center;overflow-wrap:anywhere}
.delta-life span.active{border-top-color:var(--delta-accent);color:var(--delta-ink);font-weight:700}
.tone-good{color:var(--delta-good);font-weight:650}.tone-warn{color:var(--delta-warn);font-weight:650}
.tone-serious{color:var(--delta-serious);font-weight:650}.tone-muted{color:var(--delta-faint);font-weight:650}.tone-neutral{color:var(--delta-muted);font-weight:650}
.small{color:var(--delta-muted);font-size:.78rem}
[data-testid="stMetric"]{background:transparent;border-top:1px solid var(--delta-line);padding-top:.65rem}
[data-testid="stMetricValue"]{font-size:1.35rem}
[data-testid="stExpander"]{border:1px solid var(--delta-line);border-radius:6px;background:var(--delta-surface)}
[data-testid="stDataFrame"]{border:1px solid var(--delta-line)}
.stButton>button,.stDownloadButton>button{border-radius:6px;min-height:2.5rem}
[data-testid="stBaseButton-primary"]{background:var(--delta-accent);border-color:var(--delta-accent);color:var(--delta-primary-ink)}
@media(prefers-color-scheme:dark){
  :root{
    --delta-bg:#0B0F14;--delta-surface:#121820;--delta-soft:#18212B;
    --delta-ink:#E6EDF3;--delta-muted:#8B949E;--delta-faint:#8B949E;
    --delta-line:rgba(255,255,255,0.08);--delta-sidebar:#121820;
    --delta-good:#7bc88b;--delta-warn:#d8a847;--delta-serious:#e07b62;
    --delta-primary-ink:#E6EDF3;
  }
  [data-testid="stAppViewContainer"], [data-testid="stHeader"]{background:var(--delta-bg)}
  [data-testid="stSidebar"]{background:var(--delta-sidebar)}
  [data-testid="stToolbar"], [data-testid="stDecoration"]{background:transparent}
  [data-testid="stMarkdownContainer"], [data-testid="stMetricLabel"], [data-testid="stCaptionContainer"]{color:var(--delta-muted)}
  h1,h2,h3,[data-testid="stMetricValue"]{color:var(--delta-ink)}
  .delta-decision,[data-testid="stExpander"]{background:var(--delta-surface)}
  [data-testid="stMetric"],[data-testid="stDataFrame"]{background:transparent}
  .delta-step.active{background:rgba(23,105,194,.16)}
  .delta-status.good{color:var(--delta-good);border-color:rgba(123,200,139,.38);background:rgba(31,116,56,.18)}
  .delta-status.warn{color:var(--delta-warn);border-color:rgba(216,168,71,.38);background:rgba(154,104,0,.18)}
  .delta-status.serious{color:var(--delta-serious);border-color:rgba(224,123,98,.38);background:rgba(180,73,36,.18)}
}
@media(max-width:720px){
  [data-testid="stMainBlockContainer"]{padding-left:1rem;padding-right:1rem;padding-top:1.25rem}
  .delta-brandline{display:block;line-height:1.4}
  .delta-brandline span{display:block;white-space:normal}
  .delta-brandline .sep{display:none}
  h1{font-size:1.75rem!important}.delta-steps{grid-template-columns:1fr}.delta-step{border-right:0;border-bottom:1px solid var(--delta-line)}
  .delta-step:last-child{border-bottom:0}.delta-relation-head{display:block}.delta-life span{font-size:.58rem}
}
</style>
"""
st.markdown(_CSS, unsafe_allow_html=True)


def _e(value: Any) -> str:
    return html.escape("—" if value is None else str(value))


def _tone(text: str, tone: str) -> str:
    return f'<span class="tone-{_e(tone)}">{_e(text)}</span>'


def render_section(number: str, title: str, copy: str) -> None:
    st.markdown(
        f"<div class='delta-section'><div class='delta-section-kicker'>{_e(number)}</div>"
        f"<div class='delta-section-title'>{_e(title)}</div>"
        f"<div class='delta-section-copy'>{_e(copy)}</div></div>",
        unsafe_allow_html=True,
    )


def render_pending_scroll(state: Any) -> None:
    target = state.pop("_scroll_target", None)
    if not target:
        return
    components.html(
        f"""
        <script>
        const target = parent.document.getElementById({json.dumps(target)});
        if (target) {{
          setTimeout(() => target.scrollIntoView({{behavior: "smooth", block: "start"}}), 180);
        }}
        </script>
        """,
        height=0,
    )


def set_scroll_on_success(state: Any, result: "api.ApiResult", success_views: tuple[str, ...], target: str) -> None:
    view = rl.classify_response(result.status, result.body, result.transport)
    if view in success_views:
        state["_scroll_target"] = target


def render_metric(container: Any, label: str, value: Any, note: Any = None) -> None:
    """Render supporting text without Streamlit's directional delta arrow."""
    container.metric(label, value)
    if note:
        container.caption(str(note))


def render_steps(active: int) -> None:
    labels = (("01", "Choose data"), ("02", "Audit & declare"), ("03", "Read report"))
    parts = []
    for index, (number, label) in enumerate(labels, start=1):
        state = "active" if index == active else ("done" if index < active else "")
        parts.append(f"<div class='delta-step {state}'><b>{number}</b>{_e(label)}</div>")
    st.markdown(f"<div class='delta-steps'>{''.join(parts)}</div>", unsafe_allow_html=True)


def current_phase(mode: str, state: Mapping[str, Any]) -> int:
    keys = {
        "Bundled case": ("audit", "report"),
        "Upload CSV": ("audit_up", "report_up"),
        "Eurostat": ("audit_e", "report_e"),
    }
    audit_key, report_key = keys[mode]
    if state.get(report_key):
        return 3
    if state.get(audit_key):
        return 2
    return 1


def render_error(view: str, result: "api.ApiResult") -> None:
    body = result.body or {}
    if view == "unreachable":
        st.error(f"Backend unreachable at `{api.base_url()}`.")
        return
    if view == "timeout":
        st.error("The analysis request timed out before the backend responded.")
        return
    if view == "malformed":
        st.error("The backend response is not valid Report JSON v1.")
        if result.raw:
            st.code(result.raw[:1000])
        return
    err = rl.error_display(body)
    titles = {
        "validation_error": "Input rejected",
        "not_found": "Case not found",
        "analysis_failure": "Analysis failed",
    }
    st.error(f"**{titles.get(view, view)}** · `{err.get('code') or 'unknown'}`")
    st.write(err.get("message") or "No error message was returned.")
    if err.get("field"):
        st.caption(f"Field: {err['field']}")
    if err.get("detail"):
        with st.expander("Technical detail"):
            st.json(err["detail"])


def render_snapshot(body: Mapping[str, Any]) -> None:
    summary = rl.snapshot_summary(body)
    provenance = summary.get("provenance") or {}
    updated = None
    if isinstance(provenance, Mapping):
        series = provenance.get("series") or []
        if series and isinstance(series[0], Mapping):
            updated = series[0].get("updated")
    st.markdown("#### Frozen snapshot")
    columns = st.columns(4)
    columns[0].metric("Rows", summary["row_count"] if summary["row_count"] is not None else "—")
    columns[1].metric("Source", summary["source"] or "—")
    columns[2].metric("Series", max(len(summary["columns"] or []) - 1, 0))
    columns[3].metric("Updated", updated or "—")
    st.markdown(f"<div class='delta-context'>SHA-256 · <code>{_e(summary['hash'])}</code></div>", unsafe_allow_html=True)
    if summary["has_csv"] and body.get("csv_base64"):
        st.download_button(
            "Download snapshot CSV",
            data=base64.b64decode(body["csv_base64"]),
            file_name="delta_snapshot.csv",
            mime="text/csv",
        )


def render_audit_and_declarations(
    body: Mapping[str, Any], *, key_prefix: str
) -> tuple[dict[str, str], bool]:
    data_audit = body.get("data_audit") or {}
    axis = rl.date_axis_summary(data_audit)
    rows = rl.audit_signal_rows(data_audit)
    persistent = [row for row in rows if row["persistent"]]

    st.markdown("<span id='delta-analysis-section' class='delta-scroll-anchor'></span>", unsafe_allow_html=True)
    render_section(
        "02",
        "Audit the data and declare transforms",
        "Delta reports persistence risk before scoring any relationship. The flag is advisory; an unsafe raw-level declaration is refused.",
    )
    status_class = "good" if axis["continuous"] and not axis["duplicates"] else "serious"
    status_text = "passes intake" if status_class == "good" else "intake issue"
    st.markdown(f"<span class='delta-status {status_class}'>{status_text}</span>", unsafe_allow_html=True)

    metrics = st.columns(4)
    render_metric(metrics[0], "Month axis", f"{axis['present']}/{axis['expected']}", "continuous" if axis["continuous"] else "gaps")
    metrics[1].metric("Duplicates", len(axis["duplicates"]))
    metrics[2].metric("Signals", len(rows))
    metrics[3].metric("Persistence flags", len(persistent))
    if axis["missing"]:
        st.warning("Missing months: " + ", ".join(map(str, axis["missing"])))
    if axis["duplicates"]:
        st.warning("Duplicate months: " + ", ".join(map(str, axis["duplicates"])))

    st.dataframe(
        [
            {
                "signal": row["signal"],
                "samples": row["sample_count"],
                "adjustment": row["seasonal_adjustment"],
                "unit": row["unit"],
                "coverage": row["coverage"],
                "lag-1 ACF": rl.fmt_number(row["lag1_acf"]),
                "risk": "persistent" if row["persistent"] else "clear",
            }
            for row in rows
        ],
        width="stretch",
        hide_index=True,
    )
    st.caption("Persistence means lag-1 ACF > 0.95. It is an intake risk flag, not a formal stationarity test.")

    diagnostics = body.get("transform_diagnostics") or []
    persistent_by_signal = {row["signal"]: row["persistent"] for row in rows}
    declarations: dict[str, str] = {}
    st.markdown("#### Transform declarations")
    for diagnostic in diagnostics:
        signal = diagnostic.get("signal")
        declared = diagnostic.get("declared", "none")
        flagged = persistent_by_signal.get(signal, bool(diagnostic.get("highly_persistent_risk")))
        left, right = st.columns([2, 3])
        risk = "persistent · diff suggested" if flagged else "no persistence flag"
        left.markdown(
            f"**{signal}**  \n<span class='small'>ACF {rl.fmt_number(diagnostic.get('lag1_acf'))} · {_e(risk)}</span>",
            unsafe_allow_html=True,
        )
        index = presets.TRANSFORMS.index(declared) if declared in presets.TRANSFORMS else 0
        choice = right.radio(
            str(signal),
            presets.TRANSFORMS,
            index=index,
            horizontal=True,
            label_visibility="collapsed",
            key=f"{key_prefix}_tf_{signal}",
        )
        declarations[str(signal)] = choice
        if flagged and choice == "none":
            right.markdown(_tone("Persistent series on raw levels will be rejected.", "serious"), unsafe_allow_html=True)
        else:
            right.caption("Raw levels" if choice == "none" else f"Scored on {choice} series")

    conflicts = [
        signal
        for signal, choice in declarations.items()
        if persistent_by_signal.get(signal) and choice == "none"
    ]
    if conflicts:
        st.error(
            "Analysis blocked. Declare `diff` or `log_diff` for: "
            + ", ".join(f"`{signal}`" for signal in conflicts)
        )
    else:
        st.markdown("<span class='delta-status good'>ready for analysis · past-only</span>", unsafe_allow_html=True)
    return declarations, not conflicts


def render_lifecycle(state: Any) -> None:
    spans = "".join(
        f"<span class='{'active' if step['active'] else ''}'>{_e(step['label'])}</span>"
        for step in rl.lifecycle_steps(state)
    )
    st.markdown(f"<div class='delta-life'>{spans}</div>", unsafe_allow_html=True)


def render_relation_detail(view: Mapping[str, Any], raw: Mapping[str, Any]) -> None:
    st.markdown(
        f"<div class='delta-relation-meta'>lag {_e(view['lag'])} · {_e(view['transform'])} · "
        f"weight {_e(rl.fmt_signed(view['weight']))}</div>",
        unsafe_allow_html=True,
    )
    render_lifecycle(view["lifecycle"]["state"])
    st.markdown(_tone(view["reason_text"], view["lifecycle"]["tone"]), unsafe_allow_html=True)
    evidence = st.columns(4)
    render_metric(evidence[0], "Score", rl.fmt_number(view["score"]))
    render_metric(evidence[1], "Stability", rl.fmt_number(view["stability"]), "insufficient" if view["stability"] is None else None)
    render_metric(evidence[2], "Uncertainty", rl.fmt_number(view["uncertainty"]), "insufficient" if view["uncertainty"] is None else None)
    render_metric(evidence[3], "Sample support", rl.fmt_number(view["sample_support"]), "insufficient" if view["sample_support"] is None else None)
    st.caption(
        f"p={rl.fmt_p_value(view['p_value'])} · FDR threshold={rl.fmt_p_value(view['fdr_threshold'])} · "
        f"clears FDR={'—' if view['clears_fdr'] is None else ('yes' if view['clears_fdr'] else 'no')}"
    )
    st.caption(
        "Diagnostic comparison scale: "
        f"noise floor {rl.fmt_number(view['noise_floor'])}; "
        f"effect/noise {rl.fmt_number(view['effect_size'])}. "
        "This scale is not part of the evidence gate."
    )
    if view["has_trajectory"]:
        trajectory = raw.get("trajectory") or []
        frame = pd.DataFrame(
            [
                {"date": point.get("date"), "score": point.get("score")}
                for point in trajectory
                if point.get("date") is not None and point.get("score") is not None
            ]
        )
        if frame.empty:
            st.caption("Lifecycle trajectory was returned without dated score points, so no timeline chart is shown.")
        else:
            st.line_chart(frame, x="date", y="score")
    else:
        st.caption("Lifecycle trajectory was not returned, so no timeline chart is shown.")


def render_report(body: Mapping[str, Any]) -> None:
    decision = rl.report_decision(body)
    context = rl.report_context(body)
    tone = decision["tone"]
    eyebrow = "Baseline retained" if tone == "baseline" else "Evidence gate passed"
    st.markdown(
        f"<span id='delta-report-section' class='delta-scroll-anchor'></span>"
        f"<div class='delta-section'><div class='delta-section-kicker'>03 · Report</div></div>"
        f"<div class='delta-context'>{_e(context['target'])} · {_e(context['frequency'])} · "
        f"{_e(context['observations'])} observations · as known at {_e(context['generated_as_of'])}</div>"
        f"<div class='delta-decision {tone}'><div class='eyebrow'>{_e(eyebrow)}</div>"
        f"<div class='headline'>{_e(decision['headline'])}</div>"
        f"<div class='summary'>{_e(decision['summary'])}</div></div>",
        unsafe_allow_html=True,
    )
    for line in decision["lines"][1:]:
        st.markdown(f"- {line}")

    confidence = decision["confidence"]
    metrics = st.columns(4)
    metrics[0].metric("Selected", decision["selected_count"] if decision["selected_count"] is not None else "—")
    metrics[1].metric("Final mode", decision["final_mode"] or "—")
    render_metric(metrics[2], "Confidence", confidence["text"] if not confidence["is_null"] else "—", "insufficient" if confidence["is_null"] else None)
    baseline = body.get("baseline") or {}
    render_metric(metrics[3], "Baseline MAE", rl.fmt_number(baseline.get("mae")), baseline.get("name") or "persistence")

    evaluation = rl.evaluation_interval(body)
    if evaluation:
        resolution = "resolves" if evaluation["resolves"] else "unresolved · interval spans zero"
        st.markdown(
            f"**Rolling-origin skill:** median {rl.fmt_percent(evaluation['median'])} · "
            f"90% interval [{rl.fmt_percent(evaluation['low'])}, {rl.fmt_percent(evaluation['high'])}] · "
            f"{evaluation['folds']} folds · {resolution}"
        )
    else:
        st.info("Out-of-sample evaluation is not available for this report. No interval or chart is inferred.")

    for warning in body.get("warnings") or []:
        st.warning(str(warning))

    st.markdown("### Relationship evidence")
    views = rl.relation_views(body)
    raw_relations = body.get("relations") or []
    if not views:
        st.info("The report contains no candidate relationship rows.")
    for index, view in enumerate(views):
        raw = raw_relations[index] if index < len(raw_relations) else {}
        selection = "insufficient" if view["selected"] is None else ("selected" if view["selected"] else "not selected")
        label = (
            f"{view['source']} → {view['target']} · "
            f"{view['lifecycle']['label']} · {selection}"
        )
        with st.expander(label, expanded=view["selected"] is True):
            render_relation_detail(view, raw)

    with st.expander("Analyst table"):
        st.dataframe(
            [
                {
                    "selected": "—" if view["selected"] is None else ("yes" if view["selected"] else "no"),
                    "relation": f"{view['source']} → {view['target']}",
                    "lag": view["lag"],
                    "transform": view["transform"],
                    "weight": rl.fmt_signed(view["weight"]),
                    "score": rl.fmt_number(view["score"]),
                    "noise floor": rl.fmt_number(view["noise_floor"]),
                    "stability": rl.fmt_number(view["stability"]),
                    "uncertainty": rl.fmt_number(view["uncertainty"]),
                    "lifecycle": view["lifecycle"]["label"],
                    "reason": view["reason_code"],
                }
                for view in views
            ],
            width="stretch",
            hide_index=True,
        )

    st.download_button(
        "Download Report JSON",
        data=json.dumps(body, indent=2, sort_keys=True),
        file_name=rl.report_filename(body),
        mime="application/json",
    )
    st.caption(
        f"Snapshot {_e(context['snapshot_source'])} · SHA-256 {_e(context['snapshot_hash'])} · "
        f"schema {body.get('schema_version', '—')}"
    )


def show_result(result: "api.ApiResult") -> str:
    view = rl.classify_response(result.status, result.body, result.transport)
    if rl.is_error_view(view):
        render_error(view, result)
    return view


st.markdown(
    "<div class='delta-brandline'><span>Nestor Delta</span><span class='sep'>·</span><span>evidence before certainty</span></div>",
    unsafe_allow_html=True,
)
st.title("Relationship Reliability Workbench")
st.markdown(
    "<div class='delta-lede'>Audit monthly data, declare how each signal is transformed, and see which directed relationships survive FDR, stability, uncertainty, and sample-support checks.</div>",
    unsafe_allow_html=True,
)

with st.sidebar:
    st.markdown("### Analysis workspace")
    mode = st.radio("Data source", ["Bundled case", "Upload CSV", "Eurostat"], key="data_source")
    st.divider()
    health = api.health()
    health_view = rl.classify_response(health.status, health.body, health.transport)
    status = "reachable" if health.status == 200 else health_view
    st.caption(f"Backend · {status}")
    st.code(api.base_url(), language=None)
    st.caption("Report schema · delta.report.v1")

ss = st.session_state
render_pending_scroll(ss)
render_steps(current_phase(mode, ss))
render_section("01", "Choose data", "Start from a bundled case, an aligned monthly CSV, or a verified Eurostat definition.")

if mode == "Bundled case":
    case = st.selectbox(
        "Bundled case",
        presets.BUNDLED_CASES,
        index=presets.BUNDLED_CASES.index(presets.DEFAULT_CASE),
    )
    st.caption("Bundled cases are frozen repository inputs with explicit transform declarations.")
    if st.button("Audit data", type="primary", key="audit_case"):
        with st.spinner("Auditing data..."):
            ss["audit"] = api.audit({"case_name": case})
        ss["case_name"] = case
        ss.pop("report", None)
        ss.pop("report_request", None)
        set_scroll_on_success(ss, ss["audit"], ("audit_ok",), "delta-analysis-section")
        st.rerun()

    current_request = None
    if ss.get("audit") and ss.get("case_name") == case:
        view = show_result(ss["audit"])
        if view == "audit_ok":
            declarations, allowed = render_audit_and_declarations(ss["audit"].body, key_prefix="case")
            current_request = {"case_name": case, "transform_declarations": declarations}
            if st.button("Run analysis", disabled=not allowed, type="primary", key="analyze_case"):
                with st.spinner("Analyzing relationships..."):
                    ss["report"] = api.analyze(current_request)
                ss["report_request"] = current_request
                set_scroll_on_success(ss, ss["report"], ("report_ok", "report_baseline"), "delta-report-section")
                st.rerun()
    if ss.get("report") and ss.get("report_request") == current_request:
        report_view = show_result(ss["report"])
        if report_view in ("report_ok", "report_baseline"):
            render_report(ss["report"].body)
    elif ss.get("report") and current_request is not None:
        st.info("The case or transform declarations changed. Run the analysis again to replace the previous report.")

elif mode == "Upload CSV":
    uploaded = st.file_uploader("Aligned monthly CSV", type=["csv"])
    left, right = st.columns(2)
    date_column = left.text_input("Date column", "date")
    train_end = right.text_input("Training cutoff (YYYY-MM)", "")
    target = left.text_input("Target signal", "")
    lag_window = right.number_input("Lag window", 1, 12, 3)
    signals = st.text_input("Candidate signals", "", placeholder="signal_a, signal_b")
    if uploaded and target and signals and train_end:
        signal_list = [signal.strip() for signal in signals.split(",") if signal.strip()]
        payload = {
            "csv_base64": base64.b64encode(uploaded.getvalue()).decode("ascii"),
            "date_column": date_column,
            "target": target,
            "candidate_signals": signal_list,
            "train_end": train_end,
            "lag_window": int(lag_window),
            "transform_declarations": {value: "diff" for value in [target, *signal_list]},
        }
        if st.button("Audit data", type="primary", key="audit_upload"):
            with st.spinner("Auditing uploaded data..."):
                ss["audit_up"] = api.audit(payload)
            ss["payload_up"] = payload
            ss.pop("report_up", None)
            ss.pop("report_up_request", None)
            set_scroll_on_success(ss, ss["audit_up"], ("audit_ok",), "delta-analysis-section")
            st.rerun()

        current_upload_request = None
        if ss.get("audit_up") and ss.get("payload_up") == payload:
            view = show_result(ss["audit_up"])
            if view == "audit_ok":
                declarations, allowed = render_audit_and_declarations(ss["audit_up"].body, key_prefix="upload")
                current_upload_request = dict(payload)
                current_upload_request["transform_declarations"] = declarations
                if st.button("Run analysis", disabled=not allowed, type="primary", key="analyze_upload"):
                    with st.spinner("Analyzing relationships..."):
                        ss["report_up"] = api.analyze(current_upload_request)
                    ss["report_up_request"] = current_upload_request
                    set_scroll_on_success(ss, ss["report_up"], ("report_ok", "report_baseline"), "delta-report-section")
                    st.rerun()
        if ss.get("report_up") and ss.get("report_up_request") == current_upload_request:
            report_view = show_result(ss["report_up"])
            if report_view in ("report_ok", "report_baseline"):
                render_report(ss["report_up"].body)
        elif ss.get("report_up") and current_upload_request is not None:
            st.info("The upload or transform declarations changed. Run the analysis again to replace the previous report.")
    else:
        st.caption("Choose a CSV and identify its target, candidate signals, and training cutoff.")

else:
    st.info("Eurostat catalog search is not part of W5. Use the verified preset or provide an exact dataset/filter definition.")
    preset_id = st.selectbox(
        "Verified definition",
        ["(manual)", *presets.EUROSTAT_PRESETS],
        format_func=lambda value: value if value == "(manual)" else presets.preset_label(value),
    )
    preset = presets.EUROSTAT_PRESETS.get(preset_id, {})
    default_series = json.dumps(
        preset.get("series", [{"name": "", "dataset": "", "filters": {"freq": "M", "geo": ""}}]),
        indent=2,
    )
    with st.expander("Eurostat series definition", expanded=preset_id == "(manual)"):
        series_json = st.text_area("Series JSON", default_series, height=220, key=f"series_json_{preset_id}")
    left, middle, right = st.columns(3)
    start = left.text_input("Start (YYYY-MM)", preset.get("start", ""), key=f"start_{preset_id}")
    end = middle.text_input("End (YYYY-MM)", preset.get("end", ""), key=f"end_{preset_id}")
    lag_window = right.number_input("Lag window", 1, 12, int(preset.get("lag_window", 3)), key=f"lag_{preset_id}")
    target = st.text_input("Target signal", preset.get("target", ""), key=f"target_{preset_id}")
    candidate_text = st.text_input(
        "Candidate signals",
        ",".join(preset.get("candidate_signals", [])),
        key=f"candidates_{preset_id}",
    )
    train_end = st.text_input("Training cutoff (YYYY-MM)", preset.get("train_end", ""), key=f"train_{preset_id}")
    try:
        series = json.loads(series_json) if series_json.strip() else []
        series_error = None
    except json.JSONDecodeError as exc:
        series, series_error = [], str(exc)
        st.error(f"Series JSON is invalid: {series_error}")
    candidates = [signal.strip() for signal in candidate_text.split(",") if signal.strip()]
    eurostat_request: dict[str, Any] = {"series": series, "start": start, "end": end}
    if preset_id != "(manual)":
        eurostat_request["snapshots"] = presets.frozen_snapshot_payload(preset_id)
    euro_request = {
        "eurostat": eurostat_request,
        "target": target,
        "candidate_signals": candidates,
        "train_end": train_end,
        "lag_window": int(lag_window),
        "transform_declarations": {value: "diff" for value in [target, *candidates]},
    }
    fetch_disabled = bool(series_error or not series or not target or not candidates or not start or not end or not train_end)
    if st.button("Fetch and freeze data", disabled=fetch_disabled, type="primary", key="fetch_eurostat"):
        with st.spinner("Fetching and freezing Eurostat data..."):
            ss["snap"] = api.snapshot(euro_request)
        ss["euro_request"] = euro_request
        ss.pop("audit_e", None)
        ss.pop("report_e", None)
        ss.pop("report_e_request", None)
        st.rerun()

    frozen_payload = None
    if ss.get("snap") and ss.get("euro_request") == euro_request:
        view = show_result(ss["snap"])
        if view == "snapshot_ready":
            render_snapshot(ss["snap"].body)
            frozen_payload = rl.frozen_snapshot_payload(ss["snap"].body, ss["euro_request"])
            if st.button("Audit frozen snapshot", key="audit_eurostat"):
                with st.spinner("Auditing the frozen snapshot..."):
                    ss["audit_e"] = api.audit(frozen_payload)
                ss["audit_e_request"] = frozen_payload
                ss.pop("report_e", None)
                ss.pop("report_e_request", None)
                set_scroll_on_success(ss, ss["audit_e"], ("audit_ok",), "delta-analysis-section")
                st.rerun()

    current_euro_request = None
    if ss.get("audit_e") and frozen_payload is not None and ss.get("audit_e_request") == frozen_payload:
        view = show_result(ss["audit_e"])
        if view == "audit_ok":
            declarations, allowed = render_audit_and_declarations(ss["audit_e"].body, key_prefix="eurostat")
            current_euro_request = dict(frozen_payload)
            current_euro_request["transform_declarations"] = declarations
            if st.button("Run analysis", disabled=not allowed, type="primary", key="analyze_eurostat"):
                with st.spinner("Analyzing the frozen snapshot..."):
                    ss["report_e"] = api.analyze(current_euro_request)
                ss["report_e_request"] = current_euro_request
                set_scroll_on_success(ss, ss["report_e"], ("report_ok", "report_baseline"), "delta-report-section")
                st.rerun()
    if ss.get("report_e") and ss.get("report_e_request") == current_euro_request:
        report_view = show_result(ss["report_e"])
        if report_view in ("report_ok", "report_baseline"):
            render_report(ss["report_e"].body)
    elif ss.get("report_e") and current_euro_request is not None:
        st.info("The Eurostat definition or transforms changed. Run the analysis again to replace the previous report.")
