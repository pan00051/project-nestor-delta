# Website W5 — Acceptance Record

Date: 2026-08-19. Contract: `delta.report.v1`.

## Delivered

- Unified the W4 controls into a three-step user journey: choose data, audit and
  declare, read report.
- Applied the approved audit prototype's restrained visual language to live
  Streamlit components.
- Added a conclusion-first report, compact relation disclosures, lifecycle
  tracks, honest evaluation states, and Report JSON download.
- Preserved the W4 HTTP-only boundary and hash-bound Eurostat snapshot flow.

## Corrections made during live review

- Removed Streamlit metric delta arrows from descriptive labels such as
  `insufficient`, `persistence`, and `noise floor`; those arrows falsely implied
  directional improvement.
- Collapsed non-selected relation evidence by default so the report is scannable.
- Kept selected relations eligible for expanded evidence without changing their
  selection value.

## Automated verification

- Frontend contract/display tests: **22 passed**.
- Full repository suite: **132 passed**.
- `compileall`: passed.
- `git diff --check`: passed.
- Frontend isolation check: no import of the `nestor_delta` algorithm package.

## Live verification

- Bundled Spain retail: audit returned 216/216 continuous months and two
  persistence flags; analysis returned a successful baseline-only report with
  four relation disclosures, null confidence shown as insufficient, and Report
  JSON download.
- Transform invalidation: changing persistent `hicp` to `none` disabled the Run
  button, displayed the blocking explanation, and hid the old report.
- Eurostat preset `ei_bssi_m_r2`: fetched and froze 228 months, preserved SHA-256
  `7f16537206cbb37b1b3b9ee33b9b233eb6b50865d59a03169d3651a30a3664ca`, then
  completed audit and baseline-only analysis from the frozen CSV.
- Responsive geometry: desktop and 433 px effective narrow view had no page-level
  horizontal overflow; the viewport override was reset after inspection.
- Browser console: no errors after the final reload.

## Remaining product work

W5 intentionally does not implement Eurostat catalog search, report persistence,
shareable URLs, accounts, PDF export, or deployment configuration. Those require
a separately approved sprint and, for catalog search/history, new backend
contracts.
