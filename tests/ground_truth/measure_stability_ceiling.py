#!/usr/bin/env python3
"""
S-GT-5 measurement — the stability ceiling for non-stationary relationships.

This answers the question that decides whether a real `ok` case is reachable at
all, and it is a measurement, not a pass/fail test.

The M0 run showed the Eurostat preset's best candidate rejected at
`stability = 0.047` against a gate of 0.45, while the time-invariant synthetic
control reached 0.65. Ten-fold gaps have two readings, and they lead to opposite
product decisions:

  (i)  real relationships genuinely drift, Delta correctly refuses to forecast
       from them, and `baseline_only` is the product working as designed; or
  (ii) the stability gate is calibrated against a temporal homogeneity that real
       data never has, so `outcome: ok` is unreachable on ANY real dataset —
       a calibration ceiling wearing the costume of discipline.

Holding beta_max fixed and varying only the time profile separates the two. If
no realistically-drifting profile clears 0.45, reading (ii) is the live one.

    python generate_ground_truth.py --drift
    python measure_stability_ceiling.py
"""
from __future__ import annotations

import json
from pathlib import Path

from test_ground_truth import FIXTURES, report_body, run_report

GATE = 0.45   # stability threshold the M0 sweep revealed as binding


def main() -> None:
    manifest = json.loads((FIXTURES / "manifest.json").read_text(encoding="utf-8"))
    drift = manifest.get("drift")
    if not drift:
        raise SystemExit("run: python generate_ground_truth.py --drift")

    rows = []
    for profile in sorted(drift):
        item = drift[profile]
        report = report_body(run_report(FIXTURES / item["file"], item["request"]))
        rel = next((r for r in report["relations"] if r["source"] == "true_driver"), {})
        rows.append({
            "profile": profile,
            "last_quarter_abs_r": item["last_quarter_abs_r"],
            "outcome": report["outcome"],
            "selected": rel.get("selected"),
            "stability": rel.get("stability"),
            "reason_code": rel.get("reason_code"),
            "lifecycle": (rel.get("lifecycle") or {}).get("state"),
            "effect_score": (rel.get("effect") or {}).get("score"),
        })

    hdr = f"{'profile':<14}{'lastQ|r|':>9}{'stability':>11}{'sel':>6}  {'lifecycle':<14}{'reason'}"
    print(hdr)
    print("-" * len(hdr))
    for r in rows:
        stab = "None" if r["stability"] is None else f"{r['stability']:.4f}"
        print(f"{r['profile']:<14}{r['last_quarter_abs_r']:>9}{stab:>11}"
              f"{str(r['selected']):>6}  {str(r['lifecycle']):<14}{r['reason_code']}")

    drifting = [r for r in rows if r["profile"] != "constant" and r["stability"] is not None]
    ceiling = max((r["stability"] for r in drifting), default=None)
    print()
    if ceiling is None:
        print("No stability reported for any drifting profile — investigate S9 before reading further.")
    elif ceiling < GATE:
        print(f"CEILING {ceiling:.4f} < gate {GATE}: no realistically-drifting relationship "
              f"clears the stability gate.\nReading (ii) is live — `outcome: ok` is likely "
              f"unreachable on real data. This is a calibration decision, not a data problem.")
    else:
        print(f"CEILING {ceiling:.4f} >= gate {GATE}: drifting relationships CAN clear the gate.\n"
              f"Reading (i) is live — the Eurostat preset's 0.047 reflects that particular "
              f"relationship, not a structural ceiling.")

    (FIXTURES / "stability_ceiling.json").write_text(
        json.dumps({"gate": GATE, "ceiling_excluding_constant": ceiling, "rows": rows}, indent=2),
        encoding="utf-8")


if __name__ == "__main__":
    main()
