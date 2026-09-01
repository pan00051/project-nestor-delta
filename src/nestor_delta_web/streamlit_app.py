"""Nestor Delta user-facing Streamlit frontend.

The frontend talks to the FastAPI adapter over HTTP and renders Report JSON v1.
It never imports `nestor_delta` or recomputes an analytic conclusion.
"""

from __future__ import annotations

import base64
import html
import json
from pathlib import Path
from typing import Any, Mapping

import pandas as pd
import streamlit as st

from nestor_delta_web import api_client as api
from nestor_delta_web import build_info as bi
from nestor_delta_web import presets
from nestor_delta_web import render_logic as rl

st.set_page_config(
    page_title="Nestor Delta — Relationship Reliability",
    page_icon="◐",
    layout="wide",
)

_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700&family=Inter:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap');
:root{
  --delta-bg:light-dark(#F1F3F4,#0B0F14);
  --delta-surface:light-dark(#fcfcfb,#121820);
  --delta-soft:light-dark(#eeeee9,#18212B);
  --delta-ink:light-dark(#11110f,#E6EDF3);
  --delta-muted:light-dark(#66645f,#8B949E);
  --delta-faint:light-dark(#8b8982,#8B949E);
  --delta-line:light-dark(#dcdad3,rgba(255,255,255,0.08));
  --delta-line-strong:light-dark(#C6CDD0,rgba(255,255,255,.14));
  --delta-accent:#35617F;
  --delta-water-soft:rgba(53,97,127,.10);
  --delta-good:light-dark(#1f7438,#7bc88b);
  --delta-warn:light-dark(#9a6800,#d8a847);
  --delta-serious:light-dark(#b44924,#e07b62);
  --delta-sidebar:light-dark(#eaeae5,#121820);
  --delta-primary-ink:light-dark(#fcfcfb,#E6EDF3);
  --delta-status-good-bg:light-dark(#eef6ef,rgba(31,116,56,.18));
  --delta-status-good-line:light-dark(#a9c9b2,rgba(123,200,139,.38));
  --delta-status-warn-bg:light-dark(#fbf5e5,rgba(154,104,0,.18));
  --delta-status-warn-line:light-dark(#dbc99a,rgba(216,168,71,.38));
  --delta-status-serious-bg:light-dark(#fbede7,rgba(180,73,36,.18));
  --delta-status-serious-line:light-dark(#dfb39f,rgba(224,123,98,.38));
}
[data-testid="stAppViewContainer"], [data-testid="stHeader"]{background:var(--delta-bg);color:var(--delta-ink)}
[data-testid="stAppViewContainer"]{font-family:"Inter",system-ui,sans-serif;overflow-x:hidden}
.block-container,[data-testid="stMainBlockContainer"]{max-width:1040px;padding-top:2.6rem!important;padding-bottom:5rem}
[data-testid="stSidebar"]{background:var(--delta-sidebar);border-right:1px solid var(--delta-line)}
h1,h2,h3,p,div{letter-spacing:0}
h1{font-size:2.15rem!important;line-height:1.12!important;margin-bottom:.45rem!important;color:var(--delta-ink)}
h2{font-size:1.25rem!important;margin-top:2.25rem!important}
h3{font-size:1rem!important}
[data-testid="stMarkdownContainer"] h1,[data-testid="stMarkdownContainer"] h2,[data-testid="stMarkdownContainer"] h3{color:var(--delta-ink)!important}
.delta-brandline{display:block;max-width:100%;overflow:visible;white-space:normal;min-height:1.45em;padding:.08rem 0 .75rem;margin:0 0 1.15rem;border-bottom:1px solid var(--delta-water-soft);font-size:.76rem;line-height:1.45;text-transform:uppercase;color:var(--delta-faint);font-weight:650}
.delta-wordmark{font-family:"Space Grotesk",system-ui,sans-serif;font-weight:700;color:var(--delta-ink)}
.delta-brandline span{display:inline;white-space:nowrap}
.delta-brandline .sep{display:inline-block;margin:0 .35rem}
.delta-lede{max-width:760px;color:var(--delta-muted);font-size:.95rem;line-height:1.6;margin-bottom:1.4rem}
.delta-section{border-top:1px solid var(--delta-line);padding-top:1.1rem;margin-top:1.8rem}
.delta-section-kicker{font-size:.72rem;letter-spacing:.08em;text-transform:uppercase;color:var(--delta-faint);font-weight:700}
.delta-section-title{font-size:1.1rem;font-weight:700;color:var(--delta-ink);margin:.15rem 0 .2rem}
.delta-section-copy{font-size:.86rem;color:var(--delta-muted);max-width:760px}
.delta-steps{display:grid;grid-template-columns:repeat(3,1fr);border-top:1px solid var(--delta-line);border-bottom:1px solid var(--delta-line);margin:1.25rem 0 1.6rem}
.delta-step{padding:.72rem .8rem;color:var(--delta-faint);font-size:.78rem;border-right:1px solid var(--delta-line)}
.delta-step:last-child{border-right:0}.delta-step b{display:block;color:inherit;font-size:.68rem;text-transform:uppercase;letter-spacing:.06em;margin-bottom:.12rem}
.delta-step.active{color:var(--delta-accent);background:rgba(53,97,127,.06)}
.delta-step.done{color:var(--delta-muted)}
.delta-decision{border-left:4px solid var(--delta-accent);padding:1.25rem 1.35rem;background:var(--delta-surface);margin:.8rem 0 1rem}
.delta-decision.baseline{border-left-color:var(--delta-ink)}
.delta-decision.selected{border-left-color:var(--delta-accent)}
.delta-decision .eyebrow{font-size:.7rem;text-transform:uppercase;letter-spacing:.08em;color:var(--delta-faint);font-weight:700}
.delta-decision .headline{font-family:"Space Grotesk",system-ui,sans-serif;font-size:2.4rem;line-height:1.05;font-weight:700;margin:.3rem 0;color:var(--delta-ink)}
.delta-decision .summary{font-size:.9rem;line-height:1.55;color:var(--delta-muted);max-width:800px}
.delta-decision .gate-explanation{font-size:.83rem;line-height:1.5;color:var(--delta-muted);max-width:800px;margin-top:.35rem}
.delta-decision .success-statement{font-size:.84rem;line-height:1.5;color:var(--delta-ink);font-weight:650;max-width:800px;margin-top:.45rem}
.delta-context{font-size:.78rem;color:var(--delta-muted);padding:.55rem 0;border-bottom:1px solid var(--delta-line);overflow-wrap:anywhere}
.delta-scoreboard{font-family:"IBM Plex Mono",ui-monospace,monospace;font-variant-numeric:tabular-nums;font-size:.82rem;color:var(--delta-muted);padding:.15rem 0 1.05rem}
.delta-keycard{border-top:1px solid var(--delta-line-strong);border-bottom:1px solid var(--delta-line);padding:1rem 0 1.1rem;margin:1rem 0 1.35rem}
.delta-keycard.fix{border-left:4px solid var(--delta-accent);border-top:0;background:var(--delta-surface);padding:1rem 1.15rem}
.delta-reason{font-size:.92rem;color:var(--delta-ink);font-weight:650;margin:.85rem 0 .2rem}
.delta-supporting{border-top:1px solid var(--delta-line);padding-top:.65rem;margin:1.1rem 0;color:var(--delta-muted);font-size:.82rem}
.delta-plain-section{margin:1.25rem 0 .55rem;font-size:.76rem;text-transform:uppercase;color:var(--delta-faint);font-weight:700}
.delta-status{display:inline-flex;align-items:center;border:1px solid var(--delta-line);border-radius:999px;padding:.16rem .55rem;font-size:.72rem;font-weight:650;color:var(--delta-muted)}
.delta-status.good{color:var(--delta-good);border-color:var(--delta-status-good-line);background:var(--delta-status-good-bg)}
.delta-status.warn{color:var(--delta-warn);border-color:var(--delta-status-warn-line);background:var(--delta-status-warn-bg)}
.delta-status.serious{color:var(--delta-serious);border-color:var(--delta-status-serious-line);background:var(--delta-status-serious-bg)}
.delta-status.muted{color:var(--delta-faint)}
.delta-chip{display:inline-flex;align-items:center;border:1px solid var(--delta-line-strong);border-radius:999px;padding:.08rem .45rem;font-size:.72rem;color:var(--delta-muted);background:var(--delta-surface)}
.delta-chip.insufficient{background:repeating-linear-gradient(135deg,var(--delta-surface),var(--delta-surface) 5px,var(--delta-water-soft) 5px,var(--delta-water-soft) 9px)}
.fig{font-family:"IBM Plex Mono",ui-monospace,monospace;font-variant-numeric:tabular-nums}
.delta-relation{border-top:1px solid var(--delta-line);padding:.9rem 0 .25rem;margin-top:.45rem}
.delta-relation-head{display:flex;align-items:flex-start;justify-content:space-between;gap:1rem}
.delta-relation-name,.rel-name{font-family:"Space Grotesk",system-ui,sans-serif;font-weight:700;font-size:1.12rem;overflow-wrap:anywhere}.delta-relation-meta{font-size:.78rem;color:var(--delta-muted);margin-top:.16rem}
.delta-gates{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:1px;background:var(--delta-line);border:1px solid var(--delta-line);margin:.9rem 0 .45rem}
.delta-gate{background:var(--delta-surface);padding:.72rem .75rem;min-width:0}
.delta-gate.binding{background:var(--delta-water-soft)}
.delta-gate .label{font-size:.67rem;text-transform:uppercase;color:var(--delta-faint);font-weight:700}
.delta-gate .value{font-family:"IBM Plex Mono",ui-monospace,monospace;font-variant-numeric:tabular-nums;font-size:1.05rem;color:var(--delta-ink);margin-top:.18rem}
.delta-life{display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:4px;margin:.8rem 0}
.delta-life span{border-top:3px dashed var(--delta-line-strong);padding-top:.3rem;font-size:.66rem;color:var(--delta-faint);text-align:center;overflow-wrap:anywhere}
.delta-life span.active{border-top-style:solid;border-top-color:var(--delta-accent);color:var(--delta-ink);font-weight:700}
.tone-good{color:var(--delta-good);font-weight:650}.tone-warn{color:var(--delta-warn);font-weight:650}
.tone-serious{color:var(--delta-serious);font-weight:650}.tone-muted{color:var(--delta-faint);font-weight:650}.tone-neutral{color:var(--delta-muted);font-weight:650}
.small{color:var(--delta-muted);font-size:.78rem}
[data-testid="stMetric"]{background:transparent;border-top:1px solid var(--delta-line);padding-top:.65rem}
[data-testid="stMetricValue"]{font-size:1.35rem}
[data-testid="stExpander"]{border:1px solid var(--delta-line);border-radius:6px;background:var(--delta-surface)}
[data-testid="stDataFrame"]{border:1px solid var(--delta-line)}
[data-testid="stMetricLabel"], [data-testid="stCaptionContainer"]{color:var(--delta-muted)}
.stButton>button,.stDownloadButton>button{border-radius:6px;min-height:2.5rem}
[data-testid="stBaseButton-primary"]{background:var(--delta-accent);border-color:var(--delta-accent);color:var(--delta-primary-ink)}
@media(max-width:720px){
  [data-testid="stMainBlockContainer"]{padding-left:1rem;padding-right:1rem;padding-top:3.5rem}
  .delta-brandline{display:block;line-height:1.4}
  .delta-brandline span{display:block;white-space:normal}
  .delta-brandline .sep{display:none}
  h1{font-size:1.75rem!important}.delta-decision .headline{font-size:1.85rem}.delta-steps{grid-template-columns:1fr}.delta-step{border-right:0;border-bottom:1px solid var(--delta-line)}
  .delta-step:last-child{border-bottom:0}.delta-relation-head{display:block}.delta-gates{grid-template-columns:1fr 1fr}.delta-life{grid-template-columns:repeat(3,minmax(0,1fr))}.delta-life span{font-size:.58rem}
}
</style>
"""
st.markdown(_CSS, unsafe_allow_html=True)


def _e(value: Any) -> str:
    return html.escape("—" if value is None else str(value))


def _tone(text: str, tone: str) -> str:
    return f'<span class="tone-{_e(tone)}">{_e(text)}</span>'


def _fig(value: Any) -> str:
    return f'<span class="fig">{_e(value)}</span>'


def _chip(text: str, extra_class: str = "") -> str:
    classes = f"delta-chip {extra_class}".strip()
    return f'<span class="{classes}">{_e(text)}</span>'


def _display_value(value: Any, formatter: Any = rl.fmt_number) -> str:
    if rl.is_null(value):
        return _chip("insufficient evidence", "insufficient")
    return _fig(formatter(value))


def _first_existing_path(candidates: tuple[str, ...]) -> Path | None:
    for candidate in candidates:
        path = Path(candidate)
        if path.exists():
            return path
    return None


_LOGO = _first_existing_path(
    (
        "assets/nestor-delta-logo.png",
        "assets/logo.png",
        "static/nestor-delta-logo.png",
        "static/logo.png",
    )
)
if _LOGO is not None:
    st.logo(str(_LOGO))


def render_section(number: str, title: str, copy: str) -> None:
    st.markdown(
        f"<div class='delta-section'><div class='delta-section-kicker'>{_e(number)}</div>"
        f"<div class='delta-section-title'>{_e(title)}</div>"
        f"<div class='delta-section-copy'>{_e(copy)}</div></div>",
        unsafe_allow_html=True,
    )


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
    if view == "validation_error":
        detail = err.get("detail")
        detail_text = json.dumps(detail, sort_keys=True) if isinstance(detail, Mapping) else detail
        technical = " · ".join(
            _e(value)
            for value in (err.get("field"), err.get("code") or "validation_error", detail_text)
            if value
        )
        st.markdown(
            "<div class='delta-decision baseline'>"
            "<div class='eyebrow'>Input needs a fix</div>"
            f"<div class='headline'>{_e(err.get('message') or 'The input could not be analysed')}</div>"
            "<div class='gate-explanation'>Delta refused this request before analysis because an input rule was not met.</div>"
            "</div>"
            "<div class='delta-keycard fix'>"
            "<div class='delta-plain-section'>How to fix</div>"
            f"<div class='delta-reason'>{_e(err.get('message') or 'Correct the highlighted input and run the audit again.')}</div>"
            f"<div class='small'>{technical}</div>"
            "</div>",
            unsafe_allow_html=True,
        )
        return
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


def _binding_gate(view: Mapping[str, Any]) -> str:
    code = view.get("reason_code")
    if code == "insufficient_stability":
        return "stability"
    if code == "excess_relationship_uncertainty":
        return "uncertainty"
    if code == "insufficient_sample_support":
        return "sample_support"
    if code == "below_fdr_corrected_effect":
        return "score"
    if code == "selected":
        return "all"
    if rl.is_null(view.get("stability")):
        return "stability"
    if rl.is_null(view.get("uncertainty")):
        return "uncertainty"
    if rl.is_null(view.get("sample_support")):
        return "sample_support"
    return ""


def _gate_cell(label: str, value: Any, key: str, binding: str) -> str:
    classes = "delta-gate"
    if binding in (key, "all"):
        classes += " binding"
    return (
        f"<div class='{classes}'><div class='label'>{_e(label)}</div>"
        f"<div class='value'>{_display_value(value)}</div></div>"
    )


def render_relation_detail(view: Mapping[str, Any], raw: Mapping[str, Any]) -> None:
    st.markdown(
        f"<div class='rel-name'>{_e(view['source'])} → {_e(view['target'])}</div>"
        f"<div class='delta-relation-meta'>{_e(view['direction'])} direction · "
        f"lag {_fig(view['lag'])} · {_e(view['transform'])} · "
        f"weight {_fig(rl.fmt_signed(view['weight']))}</div>",
        unsafe_allow_html=True,
    )
    binding = _binding_gate(view)
    st.markdown(
        "<div class='delta-gates'>"
        f"{_gate_cell('Score', view['score'], 'score', binding)}"
        f"{_gate_cell('Stability', view['stability'], 'stability', binding)}"
        f"{_gate_cell('Uncertainty', view['uncertainty'], 'uncertainty', binding)}"
        f"{_gate_cell('Sample support', view['sample_support'], 'sample_support', binding)}"
        "</div>",
        unsafe_allow_html=True,
    )
    clears = "—" if view["clears_fdr"] is None else ("yes" if view["clears_fdr"] else "no")
    st.markdown(
        f"<div class='delta-reason'>{_e(view['reason_text'])}</div>"
        f"<div class='small'>FDR p={_fig(rl.fmt_p_value(view['p_value']))} vs threshold "
        f"{_fig(rl.fmt_p_value(view['fdr_threshold']))} · clears {_e(clears)}</div>",
        unsafe_allow_html=True,
    )
    render_lifecycle(view["lifecycle"]["state"])
    st.markdown(
        f"<div class='small'>{_e(view['lifecycle']['label'])} / stability "
        f"{_fig(rl.fmt_number(view.get('stability')))} · lifecycle label is paired with its stability value.</div>"
        f"<div class='small'>Noise-floor diagnostic: noise floor {_fig(rl.fmt_number(view['noise_floor']))}; "
        f"effect/noise {_fig(rl.fmt_number(view['effect_size']))}. This scale is not part of the evidence gate.</div>",
        unsafe_allow_html=True,
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


def render_configuration(body: Mapping[str, Any]) -> None:
    rows = rl.configuration_rows(body)
    if not rows:
        return
    with st.expander("Effective configuration"):
        st.dataframe(rows, width="stretch", hide_index=True)


def render_report(body: Mapping[str, Any]) -> None:
    decision = rl.report_decision(body)
    p0 = rl.report_p0_answers(body)
    context = rl.report_context(body)
    context_html = " / ".join(
        f"<b>{_e(item['label'])}</b> {_e(item['value'])}"
        for item in rl.context_bar_items(body)
    )
    tone = decision["tone"]
    gate = p0["gate_result"]
    success_statement = (
        f"<div class='success-statement'>{_e(gate['success_statement'])}</div>"
        if gate["success_statement"]
        else ""
    )
    st.markdown(
        f"<div class='delta-context'>{context_html}</div>"
        f"<div class='delta-decision {tone}'><div class='eyebrow'>{_e(p0['run_status'])}</div>"
        f"<div class='headline'>{_e(gate['headline'])}</div>"
        f"<div class='gate-explanation'>{_e(gate['explanation'])}</div>"
        f"{success_statement}</div>",
        unsafe_allow_html=True,
    )

    selection = p0["selection"]
    views = p0["relation_evidence"]
    raw_relations = body.get("relations") or []
    tail = decision["fit_status"] or decision["final_mode"] or "past-only evaluation"
    st.markdown(
        "<div class='delta-scoreboard'>"
        f"{_e(selection['candidate_count'])} candidates tested · "
        f"{_e(selection['selected_count'] if selection['selected_count'] is not None else '—')} cleared the gate · "
        f"{_e(tail)}</div>",
        unsafe_allow_html=True,
    )

    if not views:
        st.info("The report contains no candidate relationship rows.")
    else:
        selected_index = next((index for index, view in enumerate(views) if view["selected"] is True), None)
        if selected_index is None:
            scored = [(index, view.get("score")) for index, view in enumerate(views) if view.get("score") is not None]
            selected_index = max(scored, key=lambda item: float(item[1]))[0] if scored else 0
        key_view = views[selected_index]
        key_raw = raw_relations[selected_index] if selected_index < len(raw_relations) else {}
        st.markdown("<div class='delta-plain-section'>Key relation</div><div class='delta-keycard'>", unsafe_allow_html=True)
        render_relation_detail(key_view, key_raw)
        st.markdown("</div>", unsafe_allow_html=True)

        other_views = [(index, view) for index, view in enumerate(views) if index != selected_index]
        if other_views:
            st.markdown("<div class='delta-plain-section'>Other candidates</div>", unsafe_allow_html=True)
            for index, view in other_views:
                raw = raw_relations[index] if index < len(raw_relations) else {}
                label = (
                    f"{view['source']} → {view['target']} · "
                    f"{view['direction']} · lag {view['lag']} · "
                    f"{view['reason_text']}"
                )
                with st.expander(label, expanded=False):
                    render_relation_detail(view, raw)

    narrative_lines = decision["lines"] or [decision["summary"]]
    if narrative_lines:
        if tone == "baseline":
            st.markdown("<div class='delta-plain-section'>Narrative</div>", unsafe_allow_html=True)
            for line in narrative_lines:
                st.markdown(f"<div class='small'>{_e(line)}</div>", unsafe_allow_html=True)
        else:
            with st.expander("Report narrative"):
                for line in narrative_lines:
                    st.markdown(f"- {line}")

    confidence = decision["confidence"]
    baseline = body.get("baseline") or {}
    st.markdown(
        "<div class='delta-supporting'>"
        f"final mode {_fig(decision['final_mode'] or '—')} · "
        f"baseline MAE {_fig(rl.fmt_number(baseline.get('mae')))} · "
        f"report confidence {_display_value(confidence['value'], lambda value: confidence['text'])}"
        "</div>",
        unsafe_allow_html=True,
    )

    for warning in body.get("warnings") or []:
        st.warning(rl.warning_text(warning))

    with st.expander("Analyst detail"):
        st.dataframe(
            rl.analyst_table_rows(body),
            width="stretch",
            hide_index=True,
        )
        rows = rl.configuration_rows(body)
        if rows:
            st.markdown("#### Effective configuration")
            st.dataframe(rows, width="stretch", hide_index=True)
        evaluation = rl.evaluation_interval(body)
        if evaluation:
            resolution = "resolves" if evaluation["resolves"] else "unresolved · interval spans zero"
            st.markdown(
                f"**Rolling-origin:** median {rl.fmt_percent(evaluation['median'])} · "
                f"90% interval [{rl.fmt_percent(evaluation['low'])}, {rl.fmt_percent(evaluation['high'])}] · "
                f"{evaluation['folds']} folds · {resolution}"
            )
        else:
            st.info("Out-of-sample evaluation is not available for this report. No interval or chart is inferred.")
        st.download_button(
            "Download Report JSON",
            data=json.dumps(body, indent=2, sort_keys=True),
            file_name=rl.report_filename(body),
            mime="application/json",
        )
    st.caption(
        f"Snapshot {_e(context['snapshot_source'])} · SHA-256 {_e(context['snapshot_hash'])} · "
        f"schema {body.get('schema_version', '—')} · pipeline {_e(context['pipeline_version'])}"
    )


def show_result(result: "api.ApiResult") -> str:
    view = rl.classify_response(result.status, result.body, result.transport)
    if rl.is_error_view(view):
        render_error(view, result)
    return view


st.markdown(
    "<div class='delta-brandline'><span class='delta-wordmark'>Nestor Delta</span><span class='sep'>·</span><span>evidence before certainty</span></div>",
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
    api_revision = bi.UNKNOWN
    if isinstance(health.body, dict):
        api_revision = str(health.body.get("source_revision") or bi.UNKNOWN)
    st.caption(
        f"Source revision · web {bi.SOURCE_REVISION[:12]} · api {api_revision[:12]}"
    )

ss = st.session_state
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
        st.rerun()

    current_request = None
    if ss.get("audit") and ss.get("case_name") == case:
        view = show_result(ss["audit"])
        if view == "audit_ok":
            declarations, allowed = render_audit_and_declarations(ss["audit"].body, key_prefix="case")
            current_request = {"case_name": case, "transform_declarations": declarations}
            if st.button("Run analysis", disabled=not allowed, type="primary", key="analyze_case"):
                with st.spinner("Analysing — running the frozen S1-S10 pipeline"):
                    ss["report"] = api.analyze(current_request)
                ss["report_request"] = current_request
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
            st.rerun()

        current_upload_request = None
        if ss.get("audit_up") and ss.get("payload_up") == payload:
            view = show_result(ss["audit_up"])
            if view == "audit_ok":
                declarations, allowed = render_audit_and_declarations(ss["audit_up"].body, key_prefix="upload")
                current_upload_request = dict(payload)
                current_upload_request["transform_declarations"] = declarations
                if st.button("Run analysis", disabled=not allowed, type="primary", key="analyze_upload"):
                    with st.spinner("Analysing — running the frozen S1-S10 pipeline"):
                        ss["report_up"] = api.analyze(current_upload_request)
                    ss["report_up_request"] = current_upload_request
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
                st.rerun()

    current_euro_request = None
    if ss.get("audit_e") and frozen_payload is not None and ss.get("audit_e_request") == frozen_payload:
        view = show_result(ss["audit_e"])
        if view == "audit_ok":
            declarations, allowed = render_audit_and_declarations(ss["audit_e"].body, key_prefix="eurostat")
            current_euro_request = dict(frozen_payload)
            current_euro_request["transform_declarations"] = declarations
            if st.button("Run analysis", disabled=not allowed, type="primary", key="analyze_eurostat"):
                with st.spinner("Analysing — running the frozen S1-S10 pipeline"):
                    ss["report_e"] = api.analyze(current_euro_request)
                ss["report_e_request"] = current_euro_request
                st.rerun()
    if ss.get("report_e") and ss.get("report_e_request") == current_euro_request:
        report_view = show_result(ss["report_e"])
        if report_view in ("report_ok", "report_baseline"):
            render_report(ss["report_e"].body)
    elif ss.get("report_e") and current_euro_request is not None:
        st.info("The Eurostat definition or transforms changed. Run the analysis again to replace the previous report.")
