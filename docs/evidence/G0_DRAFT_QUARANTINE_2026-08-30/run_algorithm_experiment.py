#!/usr/bin/env python3
"""Append one algorithm-exploration measurement row to JSONL.

This runner is intentionally measurement-only. It does not tune parameters, does
not loosen Evidence Gate terms, and does not feed prediction error into
selection. Its job is to make every algorithm exploration run leave behind the
same minimal provenance and operating-characteristic record.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
GROUND_TRUTH = REPO_ROOT / "tests" / "ground_truth"
FIXTURES = GROUND_TRUTH / "fixtures"
DEFAULT_LOG = REPO_ROOT / "reports" / "algorithm_experiments.jsonl"
DEFAULT_SEED_SETS = REPO_ROOT / "docs" / "algorithm_seed_sets_v1.json"

CRITERIA_VERSION = "algorithm_exploration.v1"
DEFAULT_MAX_DETECTION_FLOOR_ABS_R = 0.60
DEFAULT_MAX_FALSE_POSITIVE_RATE = 0.10


if str(GROUND_TRUTH) not in sys.path:
    sys.path.insert(0, str(GROUND_TRUTH))
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from generate_ground_truth import build_negative, request_payload  # noqa: E402
from test_ground_truth import report_body, run_report  # noqa: E402
from nestor_delta_service.versioning import PIPELINE_VERSION  # noqa: E402


def main() -> None:
    args = _parse_args()
    seed_sets = _load_json(args.seed_sets)
    seeds = seed_sets["sets"][args.seed_set]["false_positive_negative_seeds"]
    if args.fpr_trials is not None:
        seeds = seeds[: args.fpr_trials]
    if not seeds:
        raise SystemExit(f"no seeds configured for seed set {args.seed_set!r}")

    manifest = _load_json(FIXTURES / "manifest.json")
    detection = measure_detection_floor(manifest)
    fpr = measure_false_positive_rate(seeds)
    params = {
        "seed_set": args.seed_set,
        "false_positive_seeds": seeds,
        "max_detection_floor_abs_r": args.max_detection_floor_abs_r,
        "max_false_positive_rate": args.max_false_positive_rate,
    }
    verdict = judge(
        detection_floor=detection["detection_floor_abs_r"],
        false_positive_rate=fpr["false_positive_rate"],
        max_detection_floor_abs_r=args.max_detection_floor_abs_r,
        max_false_positive_rate=args.max_false_positive_rate,
    )

    row = {
        "snapshot_id": args.snapshot_id or default_snapshot_id(manifest, params),
        "params": params,
        "pipeline_version": PIPELINE_VERSION,
        "source_revision": source_revision(),
        "detection_floor": detection,
        "fpr": fpr,
        "holdout_result": fpr if args.seed_set == "holdout" else None,
        "verdict": verdict,
        "criteria_version": CRITERIA_VERSION,
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }
    append_jsonl(args.log, row)
    print(json.dumps(row, indent=2, sort_keys=True))


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--log", type=Path, default=DEFAULT_LOG)
    parser.add_argument("--seed-sets", type=Path, default=DEFAULT_SEED_SETS)
    parser.add_argument("--seed-set", choices=("tuning", "holdout"), default="tuning")
    parser.add_argument("--fpr-trials", type=int, default=None)
    parser.add_argument("--snapshot-id", default=None)
    parser.add_argument(
        "--max-detection-floor-abs-r",
        type=float,
        default=DEFAULT_MAX_DETECTION_FLOOR_ABS_R,
    )
    parser.add_argument(
        "--max-false-positive-rate",
        type=float,
        default=DEFAULT_MAX_FALSE_POSITIVE_RATE,
    )
    return parser.parse_args()


def measure_detection_floor(manifest: dict[str, Any]) -> dict[str, Any]:
    sweep = manifest.get("sweep")
    if not sweep:
        raise SystemExit("run: python tests/ground_truth/generate_ground_truth.py --sweep")

    rows: list[dict[str, Any]] = []
    floor = None
    for key in sorted(sweep, key=lambda k: abs(sweep[k]["injected_r"])):
        item = sweep[key]
        report = report_body(run_report(FIXTURES / item["file"], item["request"]))
        selected = report["selection"]["selected_count"] > 0
        rel = next((r for r in report["relations"] if r["source"] == "true_driver"), {})
        row = {
            "fixture": key,
            "injected_r": item["injected_r"],
            "selected": selected,
            "reason_code": rel.get("reason_code"),
            "stability": rel.get("stability"),
            "effect_score": (rel.get("effect") or {}).get("score"),
            "effect_vs_noise_floor": (rel.get("effect") or {}).get(
                "effect_size_vs_noise_floor"
            ),
        }
        rows.append(row)
        if selected and floor is None:
            floor = abs(item["injected_r"])
    return {"detection_floor_abs_r": floor, "rows": rows}


def measure_false_positive_rate(seeds: list[int]) -> dict[str, Any]:
    false_positives = 0
    rows: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = Path(tmp)
        for seed in seeds:
            df = build_negative(seed)
            csv_path = tmpdir / f"negative_{seed}.csv"
            df.to_csv(csv_path, index=False)
            report = report_body(run_report(csv_path, request_payload(df, "synthetic_target")))
            selected_count = report["selection"]["selected_count"]
            selected = selected_count > 0
            if selected:
                false_positives += 1
            rows.append(
                {
                    "seed": seed,
                    "selected_count": selected_count,
                    "selected_sources": report["selection"]["selected_sources"],
                    "false_positive": selected,
                }
            )
    return {
        "seed_count": len(seeds),
        "false_positives": false_positives,
        "false_positive_rate": false_positives / len(seeds),
        "rows": rows,
    }


def judge(
    *,
    detection_floor: float | None,
    false_positive_rate: float,
    max_detection_floor_abs_r: float,
    max_false_positive_rate: float,
) -> dict[str, Any]:
    rules = []
    if detection_floor is None:
        rules.append(
            {
                "rule_id": "AEXP-V1-R1",
                "status": "FAIL",
                "message": "No sweep strength selected; detection floor is absent.",
            }
        )
    elif detection_floor > max_detection_floor_abs_r:
        rules.append(
            {
                "rule_id": "AEXP-V1-R2",
                "status": "FAIL",
                "message": (
                    f"Detection floor {detection_floor:.2f} exceeds "
                    f"{max_detection_floor_abs_r:.2f}."
                ),
            }
        )
    else:
        rules.append(
            {
                "rule_id": "AEXP-V1-R2",
                "status": "PASS",
                "message": (
                    f"Detection floor {detection_floor:.2f} is at or below "
                    f"{max_detection_floor_abs_r:.2f}."
                ),
            }
        )

    if false_positive_rate > max_false_positive_rate:
        rules.append(
            {
                "rule_id": "AEXP-V1-R3",
                "status": "FAIL",
                "message": (
                    f"False-positive rate {false_positive_rate:.0%} exceeds "
                    f"{max_false_positive_rate:.0%}."
                ),
            }
        )
    else:
        rules.append(
            {
                "rule_id": "AEXP-V1-R3",
                "status": "PASS",
                "message": (
                    f"False-positive rate {false_positive_rate:.0%} is at or below "
                    f"{max_false_positive_rate:.0%}."
                ),
            }
        )

    statuses = {rule["status"] for rule in rules}
    if "FAIL" in statuses:
        outcome = "FAIL"
    elif all(rule["status"] == "PASS" for rule in rules):
        outcome = "PASS"
    else:
        outcome = "INCONCLUSIVE"
    return {"outcome": outcome, "rules": rules}


def default_snapshot_id(manifest: dict[str, Any], params: dict[str, Any]) -> str:
    digest = hashlib.sha256()
    basis = {
        "criteria_version": CRITERIA_VERSION,
        "params": params,
        "spec": manifest["spec"],
        "fixtures": {
            name: item["sha256"]
            for name, item in sorted(manifest.get("fixtures", {}).items())
        },
        "sweep": {
            name: item["sha256"]
            for name, item in sorted(manifest.get("sweep", {}).items())
        },
    }
    digest.update(json.dumps(basis, sort_keys=True, separators=(",", ":")).encode("utf-8"))
    return f"ground_truth.{digest.hexdigest()[:16]}"


def source_revision() -> str:
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "--short=12", "HEAD"],
            cwd=REPO_ROOT,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
    except OSError:
        return "unknown"
    value = completed.stdout.strip().lower()
    if completed.returncode != 0 or not value:
        return "unknown"
    return value


def append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, sort_keys=True, separators=(",", ":")))
        handle.write("\n")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
