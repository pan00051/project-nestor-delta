#!/usr/bin/env python3
"""
S-GT-4 — detection-floor measurement (a measurement, not a pass/fail test).

This is the bridge from M0 to the question that actually matters: *why* does the
real `ei_bssi_m_r2` preset return `baseline_only`?

Sweep the injected correlation downward and record where the evidence gate stops
selecting. That number is the detector's stated sensitivity floor at n=216 with
lag <= 3, and it turns a guess into a fact:

  * Floor around |r| ~ 0.25-0.35 -> the gate is reasonable, and real monthly
    differenced macro relations simply sit below it. `baseline_only` on real data
    is then EXPLAINED, not suspicious, and the floor is a number you can quote.
  * Floor around |r| ~ 0.8+ -> the gate is mis-calibrated and nothing real will
    ever clear it. That is a bug, and finding it here costs days instead of
    surfacing during a demo.

Also the guard required by DEMO_MILESTONES_V1 M0: any threshold change must move
the positive and negative controls in the SAME direction. This sweep is how that
is measured rather than argued.

    python generate_ground_truth.py --sweep
    python measure_sensitivity.py
"""
from __future__ import annotations

import json
from pathlib import Path

from test_ground_truth import report_body, run_report

FIXTURES = Path(__file__).parent / "fixtures"


def main() -> None:
    manifest = json.loads((FIXTURES / "manifest.json").read_text(encoding="utf-8"))
    sweep = manifest.get("sweep")
    if not sweep:
        raise SystemExit("run: python generate_ground_truth.py --sweep")

    rows, floor = [], None
    for key in sorted(sweep, key=lambda k: abs(sweep[k]["injected_r"])):
        item = sweep[key]
        report = report_body(run_report(FIXTURES / item["file"], item["request"]))
        sel = report["selection"]["selected_count"] > 0
        rel = next((r for r in report["relations"] if r["source"] == "true_driver"), {})
        rows.append({
            "injected_r": item["injected_r"],
            "selected": sel,
            "reason_code": rel.get("reason_code"),
            "stability": rel.get("stability"),
            "effect_vs_noise_floor": (rel.get("effect") or {}).get("effect_size_vs_noise_floor"),
        })
        if sel and floor is None:
            floor = abs(item["injected_r"])

    print(f"{'|r|':>6}  {'selected':>8}  {'reason':<32} {'stab':>6}  {'eff/nf':>7}")
    for r in rows:
        print(f"{abs(r['injected_r']):>6.2f}  {str(r['selected']):>8}  "
              f"{str(r['reason_code']):<32} {str(r['stability']):>6}  "
              f"{str(r['effect_vs_noise_floor']):>7}")
    print(f"\nDetection floor: |r| = {floor}" if floor else "\nNothing selected at any strength — investigate the gate.")
    (FIXTURES / "sensitivity.json").write_text(
        json.dumps({"detection_floor_abs_r": floor, "rows": rows}, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
