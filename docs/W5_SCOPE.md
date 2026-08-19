# Website W5 — User Display Integration

Status: implemented against the frozen Report JSON v1 contract.

## Goal

Turn the W4 engineering workbench into one coherent user journey without
changing the API contract or any S1-S10 conclusion. The product should lead
with the decision, preserve uncertainty, and make `baseline_only` and null
values understandable rather than treating them as failures.

## In scope

- One visual system derived from the approved audit/transform prototype.
- A visible three-step flow: choose data, audit and declare, read report.
- Bundled case, aligned CSV upload, and verified/manual Eurostat definitions.
- Audit summary, per-signal persistence risk, and transform declarations.
- A conclusion-first report with case context, selected count, final mode,
  confidence, baseline, and rolling interval when the API supplies one.
- Directed relation detail with lag, transform, weight, noise floor, FDR,
  stability, uncertainty, sample support, and lifecycle track.
- Snapshot CSV and Report JSON downloads.
- Distinct validation, not-found, analysis, transport, and malformed states.
- Desktop and narrow-width browser verification.

## Out of scope

- Eurostat catalog search, free-text discovery, or fabricated search results.
- Report history, permanent URLs, sharing, accounts, authentication, or a
  database.
- PDF generation or scheduled analyses.
- LLM-written claims or any narrative that is not in Report JSON or a fixed
  outcome explanation.
- New trajectory/evaluation data, relationship-network inference, or charts
  built from values the API did not return.
- Changes to S1-S10, Report JSON v1, `/snapshot`, `/audit`, or `/analyze`.
- Migration away from the accepted FastAPI + Streamlit deployment shape.

## Integrity rules

1. The frontend never imports `nestor_delta` and never recomputes relation,
   lag, transform, stability, uncertainty, lifecycle, selection, or confidence.
2. Null stays null and is displayed as insufficient/not evaluated, never zero.
3. `baseline_only` is a successful report state.
4. Eurostat analysis uses the hash-bound CSV returned by `/snapshot`; it does
   not refetch live data for `/audit` or `/analyze`.
5. A lifecycle or evaluation chart is shown only when the corresponding data
   exists in the report.

## Acceptance

- All canonical W0 report states remain covered by pure rendering tests.
- W5 decision summary, lifecycle order, contract context, and download naming
  have direct tests.
- Bundled Spain completes audit and analysis in the live UI.
- The verified Eurostat preset completes snapshot, audit, and analysis.
- Changing a transform invalidates the visible old report.
- Desktop and narrow widths have no horizontal page overflow.
- Full repository tests, compileall, and `git diff --check` pass.
