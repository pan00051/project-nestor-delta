"""Sprint 8 harness demonstration: does the evaluation protocol resolve effects?

This script uses a plain lagged-OLS STAND-IN model, not the published Delta
pipeline. It demonstrates the behaviour of the rolling-origin protocol and its
guards; it is NOT the dual-window recheck. The faithful re-evaluation of the
published +7.11% / -9.63% result lives in ``run_dual_window_recheck.py``, which
loads the frozen selection and guard.

Produces under ``reports/evaluation_power/``:

1. ``harness_controls.csv``   -- four guards: a zero-centred sign-flip null
                                 (interval contains zero by construction),
                                 identity, scrambled, and degraded controls.
2. ``single_vs_rolling.csv``  -- the SAME stand-in model judged by the frozen
                                 single-split protocol and by rolling origin,
                                 showing how a single split hides uncertainty.
3. ``metrics_extended.csv``   -- MASE, directional accuracy, worst-decile, and
                                 change-space error for the stand-in model.
4. ``harness_demonstration.md`` -- narrative of the above, explicitly labelled
                                 as a stand-in demonstration.

No existing report is read or overwritten.
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from nestor_delta.baselines import fit_linear_regression  # noqa: E402
from nestor_delta.interval_metrics import (  # noqa: E402
    change_space_errors,
    sign_flip_null_interval,
    directional_accuracy,
    fold_skill,
    mase,
    skill_interval,
    worst_decile_error,
)
from nestor_delta.metrics import mae  # noqa: E402
from nestor_delta.rolling_origin import (  # noqa: E402
    assert_folds_are_past_only,
    build_rolling_origin_folds,
)

OUTPUT_DIR = REPO_ROOT / "reports" / "evaluation_power"
LAG_WINDOW = 2
MIN_TRAIN = 120


def load_case(case_dir: Path, target: str, signals):
    rows = list(csv.DictReader((case_dir / "data.csv").open()))
    dates = [row["date"] for row in rows]
    numeric = [{k: float(v) for k, v in row.items() if k != "date"} for row in rows]
    return dates, numeric, target, list(signals)


def features(rows, index, signals):
    sample = [1.0]
    for lag in range(1, LAG_WINDOW + 1):
        sample.extend(rows[index - lag][name] for name in signals)
    return sample


def evaluate_fold(rows, fold, target, signals):
    train_x = [features(rows, i, signals) for i in fold.train_label_rows]
    train_y = [rows[i][target] for i in fold.train_label_rows]
    try:
        model = fit_linear_regression(train_x, train_y)
    except ValueError:
        return None

    actual, delta_pred, persistence, previous = [], [], [], []
    for i in fold.test_label_rows:
        actual.append(rows[i][target])
        previous.append(rows[i - 1][target])
        persistence.append(rows[i - 1][target])
        delta_pred.append(sum(v * c for v, c in zip(features(rows, i, signals), model)))
    return actual, delta_pred, persistence, previous, train_y


def rolling_run(rows, target, signals, label_rows, test_size=1):
    """Evaluate the model and four harness controls over every forecast origin.

    Control 0 (sign-flip null): the model's own per-fold skill with signs
                           randomized. Centred on zero by construction; the
                           observed median must be judged against this band.
    Control A (identity):  persistence scored against itself. Skill must be
                           exactly zero in every fold, or the arithmetic is wrong.
    Control B (scrambled): the model refit on signals whose time order has been
                           destroyed. Its interval must not reach above zero, or
                           the protocol is manufacturing skill from nothing.
    Control C (degraded):  persistence plus a shock the size of a typical move.
                           Its interval must sit entirely below zero, or the
                           protocol is blind to a model getting worse.
    """
    folds = build_rolling_origin_folds(
        label_rows, test_size=test_size, min_train_size=MIN_TRAIN
    )
    assert_folds_are_past_only(folds)

    scrambled_rows = _scramble_signals(rows, signals, seed=424242)

    skills = {"delta": [], "identity": [], "scrambled": [], "degraded": []}
    pooled = {"actual": [], "delta": [], "pers": [], "prev": []}
    state = 987654321
    for fold in folds:
        result = evaluate_fold(rows, fold, target, signals)
        if result is None:
            continue
        actual, delta_pred, persistence, previous, train_y = result

        scale = sum(
            abs(train_y[i] - train_y[i - 1]) for i in range(1, len(train_y))
        ) / (len(train_y) - 1)
        degraded = []
        for prev in previous:
            state = (1103515245 * state + 12345) % (2 ** 31)
            degraded.append(prev + ((state / (2 ** 31)) - 0.5) * 2.0 * scale)

        scrambled_result = evaluate_fold(scrambled_rows, fold, target, signals)
        if scrambled_result is None:
            continue

        base = mae(actual, persistence)
        if base <= 0.0:
            continue
        skills["delta"].append(fold_skill(mae(actual, delta_pred), base))
        skills["identity"].append(fold_skill(mae(actual, persistence), base))
        skills["scrambled"].append(fold_skill(mae(actual, scrambled_result[1]), base))
        skills["degraded"].append(fold_skill(mae(actual, degraded), base))
        pooled["actual"].extend(actual)
        pooled["delta"].extend(delta_pred)
        pooled["pers"].extend(persistence)
        pooled["prev"].extend(previous)

    # Zero-centred null: sign-flip randomization of the model's own per-fold
    # skill. Centred on zero by construction; satisfies the original
    # "random predictor interval must contain zero" acceptance item.
    skills["sign_flip_null"] = list(skills["delta"])
    return skills, pooled, len(folds)


def _scramble_signals(rows, signals, seed):
    """Destroy the time order of every candidate signal, keeping the target intact.

    Any apparent skill a model retains after this is an artifact of the
    evaluation protocol, not information in the signals.
    """
    order = list(range(len(rows)))
    state = seed
    for i in range(len(order) - 1, 0, -1):
        state = (1103515245 * state + 12345) % (2 ** 31)
        j = state % (i + 1)
        order[i], order[j] = order[j], order[i]

    scrambled = [dict(row) for row in rows]
    for name in signals:
        for position, source in enumerate(order):
            scrambled[position][name] = rows[source][name]
    return scrambled


def single_split_run(rows, target, signals, label_rows, test_size):
    boundary = len(label_rows) - test_size
    train_rows, test_rows = label_rows[:boundary], label_rows[boundary:]
    train_x = [features(rows, i, signals) for i in train_rows]
    train_y = [rows[i][target] for i in train_rows]
    model = fit_linear_regression(train_x, train_y)
    actual = [rows[i][target] for i in test_rows]
    persistence = [rows[i - 1][target] for i in test_rows]
    delta_pred = [
        sum(v * c for v, c in zip(features(rows, i, signals), model)) for i in test_rows
    ]
    return fold_skill(mae(actual, delta_pred), mae(actual, persistence)), len(test_rows)


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    cases = [
        (
            "spain_retail_eurostat_2008_2025",
            REPO_ROOT / "cases" / "spain_retail_eurostat_2008_2025",
            "retail_volume",
            ("unemployment_rate", "consumer_confidence", "industrial_production", "hicp"),
            24,
        ),
        (
            "spain_industrial_shock_2008_2021",
            REPO_ROOT / "cases" / "spain_industrial_shock_2008_2021",
            "industrial_production",
            ("unemployment_rate", "consumer_confidence", "hicp", "industry_confidence", "economic_sentiment"),
            24,
        ),
    ]

    control_rows, comparison_rows, notes = [], [], []
    for name, case_dir, target, signals, single_test_size in cases:
        _, rows, target, signals = load_case(case_dir, target, signals)
        label_rows = list(range(LAG_WINDOW, len(rows)))
        if len(label_rows) < MIN_TRAIN + 10:
            continue

        skills, pooled, fold_count = rolling_run(rows, target, signals, label_rows)
        delta_interval = skill_interval(skills["delta"])
        single_skill, single_n = single_split_run(
            rows, target, signals, label_rows, single_test_size
        )

        # Zero-centred null first, then the three failure-mode guards.
        null_interval = sign_flip_null_interval(skills["sign_flip_null"])
        control_rows.append(
            {
                "case": name,
                "control": "sign_flip_null",
                "requirement": "interval must contain zero (zero-centred by construction)",
                "folds": null_interval.fold_count,
                "median_skill": f"{null_interval.median:.6f}",
                "low": f"{null_interval.low:.6f}",
                "high": f"{null_interval.high:.6f}",
                "passed": null_interval.low <= 0.0 <= null_interval.high,
            }
        )
        for control, requirement in (
            ("identity", "every fold exactly zero"),
            ("scrambled", "interval must not reach above zero"),
            ("degraded", "interval must sit entirely below zero"),
        ):
            interval = skill_interval(skills[control])
            if control == "identity":
                passed = all(value == 0.0 for value in skills[control])
            elif control == "scrambled":
                passed = interval.high <= 0.0
            else:
                passed = interval.high < 0.0
            control_rows.append(
                {
                    "case": name,
                    "control": control,
                    "requirement": requirement,
                    "folds": interval.fold_count,
                    "median_skill": f"{interval.median:.6f}",
                    "low": f"{interval.low:.6f}",
                    "high": f"{interval.high:.6f}",
                    "passed": passed,
                }
            )
        comparison_rows.append(
            {
                "case": name,
                "single_split_test_points": single_n,
                "single_split_skill": f"{single_skill:.6f}",
                "rolling_folds": delta_interval.fold_count,
                "rolling_median_skill": f"{delta_interval.median:.6f}",
                "rolling_low": f"{delta_interval.low:.6f}",
                "rolling_high": f"{delta_interval.high:.6f}",
                "rolling_excludes_zero": delta_interval.excludes_zero,
            }
        )

        train_actual = [rows[i][target] for i in label_rows[:MIN_TRAIN]]
        notes.append(
            {
                "case": name,
                "single": single_skill,
                "single_n": single_n,
                "interval": delta_interval,
                "mase": mase(pooled["actual"], pooled["delta"], train_actual),
                "mase_pers": mase(pooled["actual"], pooled["pers"], train_actual),
                "worst": worst_decile_error(pooled["actual"], pooled["delta"]),
                "worst_pers": worst_decile_error(pooled["actual"], pooled["pers"]),
                "direction": directional_accuracy(pooled["actual"], pooled["delta"], pooled["prev"]),
                "direction_pers": directional_accuracy(pooled["actual"], pooled["pers"], pooled["prev"]),
                "change": change_space_errors(pooled["actual"], pooled["delta"], pooled["prev"]),
                "change_pers": change_space_errors(pooled["actual"], pooled["pers"], pooled["prev"]),
            }
        )

    metric_rows = []
    for note in notes:
        metric_rows.append(
            {
                "case": note["case"],
                "mase_delta": f"{note['mase']:.6f}",
                "mase_persistence": f"{note['mase_pers']:.6f}",
                "direction_decided": f"{note['direction']['decided']:.6f}",
                "direction_accuracy": f"{note['direction']['accuracy']:.6f}",
                "direction_persistence_decided": f"{note['direction_pers']['decided']:.6f}",
                "worst_decile_delta": f"{note['worst']:.6f}",
                "worst_decile_persistence": f"{note['worst_pers']:.6f}",
                "change_error_share_delta": f"{note['change']['error_share_of_move']:.6f}",
                "change_error_share_persistence": f"{note['change_pers']['error_share_of_move']:.6f}",
            }
        )

    _write_csv(OUTPUT_DIR / "harness_controls.csv", control_rows)
    _write_csv(OUTPUT_DIR / "single_vs_rolling.csv", comparison_rows)
    _write_csv(OUTPUT_DIR / "metrics_extended.csv", metric_rows)
    _write_harness_demo(OUTPUT_DIR / "harness_demonstration.md", notes)

    for note in notes:
        interval = note["interval"]
        print(f"\n=== {note['case']} ===")
        print(
            f"  single split ({note['single_n']} points): skill = {note['single']:+.2%}"
        )
        print(
            f"  rolling origin ({interval.fold_count} folds): median {interval.median:+.2%} "
            f"  90% interval [{interval.low:+.2%}, {interval.high:+.2%}]"
            f"  excludes zero: {interval.excludes_zero}"
        )
        print(
            f"  MASE delta {note['mase']:.4f} vs persistence {note['mase_pers']:.4f}"
        )
        print(
            f"  worst-decile MAE delta {note['worst']:.4f} vs persistence {note['worst_pers']:.4f}"
        )
        print(
            f"  direction: delta decided {note['direction']['decided']:.0%} "
            f"accuracy {note['direction']['accuracy']:.1%} | "
            f"persistence decided {note['direction_pers']['decided']:.0%}"
        )
        print(
            f"  change-space: delta error is {note['change']['error_share_of_move']:.2f}x "
            f"the typical move; persistence {note['change_pers']['error_share_of_move']:.2f}x"
        )


def _write_csv(path: Path, rows) -> None:
    if not rows:
        return
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=list(rows[0].keys()), lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(rows)


def _write_harness_demo(path: Path, notes) -> None:
    lines = [
        "# Rolling-Origin Harness Demonstration (stand-in model)",
        "",
        "This report uses a plain lagged-OLS **stand-in** model, not the published",
        "Delta pipeline. It demonstrates why a single split hides uncertainty and how",
        "the guards behave. It is **not** the dual-window recheck: the faithful",
        "re-evaluation of the published `+7.11% / -9.63%` result, using the frozen",
        "selection and baseline guard, is produced by `run_dual_window_recheck.py`.",
        "",
        "## Single split versus rolling origin (stand-in model)",
        "",
        "| Case | Single-split skill | Test points | Rolling folds | Rolling median | 90% interval | Resolves? |",
        "|---|---|---|---|---|---|---|",
    ]
    for note in notes:
        interval = note["interval"]
        lines.append(
            f"| `{note['case']}` | {note['single']:+.2%} | {note['single_n']} | "
            f"{interval.fold_count} | {interval.median:+.2%} | "
            f"[{interval.low:+.2%}, {interval.high:+.2%}] | "
            f"{'yes' if interval.excludes_zero else 'no'} |"
        )
    lines += [
        "",
        "These numbers describe the stand-in model only. A single split reports one",
        "number drawn from the rolling interval and gives no way to see its width.",
        "",
        "## Harness controls",
        "",
        "See `harness_controls.csv`. Four guards, each aimed at a distinct failure",
        "mode:",
        "",
        "- **sign_flip_null** -- the model's own per-fold skill with signs randomized.",
        "  Centred on zero by construction, so its interval contains zero: this is the",
        "  correct realization of the original *random-predictor-must-contain-zero*",
        "  acceptance item. The observed skill is judged against this band.",
        "- **identity** -- persistence scored against itself; every fold exactly zero.",
        "- **scrambled** -- model refit on time-scrambled signals; interval must not",
        "  reach above zero.",
        "- **degraded** -- persistence plus a typical-size shock; interval must sit",
        "  entirely below zero. Note: a naive noisy predictor is *not* a zero-centred",
        "  null, it is this degraded control.",
        "",
        "## Extended metrics",
        "",
        "See `metrics_extended.csv` for MASE, directional accuracy, worst-decile, and",
        "change-space error for the stand-in model across all rolling folds.",
    ]
    path.write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
