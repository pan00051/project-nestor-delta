"""
Nestor Delta — S-GT-5: drift and lifecycle ground truth.

S-GT-1 injects a TIME-INVARIANT relationship, which is the upper bound for
temporal stability rather than a realistic case. These fixtures hold beta_max
fixed at the S-GT-1 level and vary only the TIME PROFILE, so the resulting
numbers isolate the effect of drift from the effect of strength.

They answer two questions the M0 controls cannot:

  Q1  Is `stability >= 0.45` reachable by a relationship that is real but
      non-stationary? If it is not, then no real dataset will ever produce
      `outcome: ok`, and what looks like product discipline is really a
      calibration ceiling. Answered by `measure_stability_ceiling.py` — a
      measurement, not an assertion.

  Q2  Does the S9 lifecycle state machine track a relationship that STOPS?
      This is a headline product claim that nothing has tested. A relation that
      ended five years ago must not be reported as `stable`. Answered by the
      assertions below.

Ground truth by construction (from fixtures/manifest.json, `drift` section):

    profile          full   1st qtr   last qtr
    constant        0.589    0.6309     0.6318   alive throughout
    linear_decay    0.3549   0.5918     0.2767   fading
    regime_off      0.4647   0.6309     0.2125   stops at 70% of the sample
    regime_late     0.5005   0.2294     0.6318   starts at 30% of the sample
    intermittent    0.3962   0.4864     0.4181   alternating 24-month blocks

Wiring: none. These reuse `run_report()` from test_ground_truth.py, so the
single adapter edit made for M0 covers this file too.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from test_ground_truth import FIXTURES, report_body, run_report

MANIFEST = json.loads((FIXTURES / "manifest.json").read_text(encoding="utf-8"))
DRIFT = MANIFEST.get("drift") or {}

ALIVE = {"birth", "strengthening", "stable"}
ENDING = {"decaying", "dead"}

pytestmark = pytest.mark.skipif(
    not DRIFT, reason="run: python generate_ground_truth.py --drift"
)


def _driver(profile: str) -> dict:
    item = DRIFT[profile]
    report = report_body(run_report(FIXTURES / item["file"], item["request"]))
    for rel in report["relations"]:
        if rel["source"] == "true_driver":
            return rel
    raise AssertionError("true_driver missing from relations[]")


@pytest.mark.parametrize("profile", sorted(DRIFT))
def test_sgt5_lifecycle_state_is_reported(profile: str) -> None:
    """Every candidate carries a lifecycle state, drifting or not."""
    rel = _driver(profile)
    state = (rel.get("lifecycle") or {}).get("state")
    assert state in ALIVE | ENDING, f"{profile}: unusable lifecycle state {state!r}"


def test_sgt5_dead_relation_is_not_reported_alive() -> None:
    """`regime_off`: the relationship is exactly zero for the final 30% of the
    sample — 65 months. Last-quarter |r| is 0.21 against 0.63 in the first
    quarter, and the 0.21 is sampling noise on 53 points, not signal.

    A state machine that calls this `stable` (or `strengthening`) is telling the
    user a relationship is intact five years after it stopped existing. That is
    the single most damaging failure mode available to this product, because it
    fails in the direction of over-claiming.

    If this fails, the likely cause is that `lifecycle.state` is computed over
    the whole sample rather than as-of the end of it.
    """
    rel = _driver("regime_off")
    state = rel["lifecycle"]["state"]
    assert state in ENDING, (
        f"relation stopped at month 151 of 216 but lifecycle.state == {state!r}; "
        "expected 'decaying' or 'dead'"
    )


def test_sgt5_late_relation_is_not_reported_dead() -> None:
    """`regime_late` is the mirror image: absent for the first 30%, then present
    and strong to the end (last-quarter |r| = 0.63). It must not read as dead."""
    rel = _driver("regime_late")
    state = rel["lifecycle"]["state"]
    assert state != "dead", "a relation strong through the final quarter was reported dead"


def test_sgt5_constant_relation_is_not_reported_decaying() -> None:
    """Control for the two above: a relationship that never changes must not be
    reported as ending. Without this, a state machine that always says `dead`
    would pass the regime_off test."""
    rel = _driver("constant")
    state = rel["lifecycle"]["state"]
    assert state in ALIVE, f"time-invariant relation reported as {state!r}"
