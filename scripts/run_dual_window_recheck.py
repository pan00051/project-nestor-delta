"""Faithful rolling-origin recheck of the published dual-window result.

Sprint 8, decision B+(i): re-evaluate the *frozen* published selection and
baseline guard across many forecast origins, WITHOUT re-selecting per fold.

The published dual-window findings state, for Case B (the shock case), a
validation gain of +7.11% and a pandemic-window loss of -9.63%. Each was a
single-window aggregate. This script keeps the frozen selected source set and
lag from ``validation_selection.json`` fixed, refits only the OLS coefficients
on each origin's past-only train window, and reports the per-origin skill as a
distribution.

Semantic guard (the trap this script exists to avoid): the -9.63% is a single
regime (the 2020-2021 pandemic). Rolling origins across the ordinary span do
NOT put an error bar on -9.63%. Instead they give the frozen model's ordinary
skill distribution; the pandemic block is then placed as its own segment
against that distribution. The two are reported separately and never merged.

Reuses the exact fit/predict path from ``real_case_analysis`` so the model is
the published model, not a stand-in. OLS is invariant to constant per-source
weight scaling, so frozen sources enter with weight 1.0 with no effect on the
fitted predictions.
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from nestor_delta.interval_metrics import fold_skill, skill_interval  # noqa: E402
from nestor_delta.metrics import mae  # noqa: E402
from nestor_delta.real_case_analysis import (  # noqa: E402
    fit_real_case_predictor,
    predict_real_case,
    predict_persistence,
)
from nestor_delta.relation_weights import RelationWeight  # noqa: E402
from nestor_delta.validation_parameter_search import load_adaptive_case  # noqa: E402

OUTPUT_DIR = REPO_ROOT / "reports" / "evaluation_power"

CASES = (
    ("spain_industrial_normal_2008_2021", "Case A (normal)"),
    ("spain_industrial_shock_2008_2021", "Case B (shock)"),
)


def frozen_selection(case_name: str) -> dict:
    path = REPO_ROOT / "reports" / case_name / "validation_selection.json"
    return json.loads(path.read_text())


def label_rows_between(dates, start, end, lag_window):
    return [
        index
        for index, date in enumerate(dates)
        if index >= lag_window and start <= date <= end
    ]


def recheck_delta_case(spec, data, selection):
    lag_window = int(selection["lag_window"])
    sources = tuple(selection["actual_ols_sources"])
    # Weight scaling is absorbed by OLS; 1.0 leaves predictions unchanged.
    selected_weights = tuple(
        RelationWeight(
            source=source,
            target=spec.target,
            lag=lag_window,
            weight=1.0,
            score=1.0,
            sample_count=0,
        )
        for source in sources
    )

    # Origins run from the first validation month through the last pandemic
    # month; each origin trains on every label row strictly before it.
    first_origin = label_rows_between(
        data.dates, spec.validation_start, spec.test_end, lag_window
    )[0]
    origins = [
        index
        for index in range(first_origin, len(data.rows))
        if data.dates[index] <= spec.test_end
    ]

    per_origin = []
    for origin in origins:
        train_label_rows = [
            index
            for index in range(lag_window, origin)
        ]
        if len(train_label_rows) <= len(selected_weights) * lag_window + lag_window:
            continue
        model = fit_real_case_predictor(
            data.rows, train_label_rows, selected_weights, spec.target, lag_window
        )
        prediction = predict_real_case(
            data.rows, [origin], model, spec.target, lag_window
        )[0]
        actual = float(data.rows[origin][spec.target])
        prev = float(data.rows[origin - 1][spec.target])
        base = abs(actual - prev)
        if base <= 0.0:
            continue
        model_err = abs(actual - prediction)
        era = "pandemic" if data.dates[origin] >= spec.test_start else "validation"
        per_origin.append(
            {
                "origin_date": data.dates[origin],
                "era": era,
                "skill": fold_skill(model_err, base),
            }
        )
    return per_origin


def block_skill(spec, data, selection, start, end):
    """Aggregate MAE-ratio skill over a whole window, published-number style."""
    lag_window = int(selection["lag_window"])
    sources = tuple(selection["actual_ols_sources"])
    selected_weights = tuple(
        RelationWeight(source=s, target=spec.target, lag=lag_window, weight=1.0,
                       score=1.0, sample_count=0)
        for s in sources
    )
    window = label_rows_between(data.dates, start, end, lag_window)
    train_label_rows = [i for i in range(lag_window, window[0])]
    model = fit_real_case_predictor(
        data.rows, train_label_rows, selected_weights, spec.target, lag_window
    )
    preds = predict_real_case(data.rows, window, model, spec.target, lag_window)
    actual = [float(data.rows[i][spec.target]) for i in window]
    pers = predict_persistence(data.rows, window, spec.target)
    base = mae(actual, pers)
    return fold_skill(mae(actual, preds), base)


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    all_rows = []
    summary_lines = [
        "# Dual-Window Recheck (frozen selection, rolling origin)",
        "",
        "Faithful re-evaluation of the published dual-window result: the frozen",
        "selected source set and lag are held fixed; only OLS coefficients are",
        "refit on each origin's past-only window. No per-fold re-selection.",
        "",
        "The published single-window numbers were `+7.11%` (Case B validation) and",
        "`-9.63%` (Case B pandemic). Below, each is placed against the frozen",
        "model's per-origin skill distribution.",
        "",
    ]

    for case_name, label in CASES:
        spec, data = load_adaptive_case(
            REPO_ROOT / "cases" / case_name / "adaptive_case.json"
        )
        selection = frozen_selection(case_name)
        summary_lines.append(f"## {label} — `{case_name}`")
        summary_lines.append("")

        if selection["final_mode"] == "baseline_only":
            summary_lines += [
                f"Frozen mode is `baseline_only`: the validation guard froze this case",
                f"to persistence, so the model IS the baseline and per-origin skill is",
                f"identically zero. There is no fitted relation to re-evaluate.",
                "",
            ]
            continue

        per_origin = recheck_delta_case(spec, data, selection)
        all_rows.extend({"case": case_name, **row} for row in per_origin)

        val = [r["skill"] for r in per_origin if r["era"] == "validation"]
        pan = [r["skill"] for r in per_origin if r["era"] == "pandemic"]
        val_iv = skill_interval(val)
        pan_iv = skill_interval(pan)
        val_block = block_skill(spec, data, selection, spec.validation_start, spec.validation_end)
        pan_block = block_skill(spec, data, selection, spec.test_start, spec.test_end)

        pandemic_inside = val_iv.low <= pan_iv.median <= val_iv.high
        summary_lines += [
            f"Frozen selection: `{', '.join(selection['actual_ols_sources'])}` at lag "
            f"`{selection['lag_window']}`.",
            "",
            f"- Validation-era block skill (my refit): `{val_block:+.2%}` "
            f"(published `+7.11%`).",
            f"- Pandemic block skill (my refit): `{pan_block:+.2%}` "
            f"(published `-9.63%`).",
            "",
            f"| Era | Origins | Per-origin median | 90% interval | Resolves? |",
            f"|---|---|---|---|---|",
            f"| validation | {val_iv.fold_count} | {val_iv.median:+.2%} | "
            f"[{val_iv.low:+.2%}, {val_iv.high:+.2%}] | "
            f"{'yes' if val_iv.excludes_zero else 'no'} |",
            f"| pandemic | {pan_iv.fold_count} | {pan_iv.median:+.2%} | "
            f"[{pan_iv.low:+.2%}, {pan_iv.high:+.2%}] | "
            f"{'yes' if pan_iv.excludes_zero else 'no'} |",
            "",
            f"**Interpretation.** The pandemic per-origin median (`{pan_iv.median:+.2%}`) "
            f"{'falls within' if pandemic_inside else 'falls OUTSIDE'} the validation-era "
            f"90% band `[{val_iv.low:+.2%}, {val_iv.high:+.2%}]`. "
            + (
                "The pandemic loss is not distinguishable from ordinary origin-to-origin "
                "variation at this sample size, so the frozen model does not establish a "
                "structural break; the single-window numbers were within noise."
                if pandemic_inside
                else
                "The pandemic block sits outside the ordinary band, consistent with a "
                "regime change rather than sampling noise."
            ),
            "",
            "Neither the validation-era nor the pandemic per-origin interval "
            + (
                "excludes zero, so on this data the frozen model's skill is not "
                "resolvable from persistence in either era."
                if not val_iv.excludes_zero and not pan_iv.excludes_zero
                else "is uniformly unresolved; see the interval flags above."
            ),
            "",
        ]

    if all_rows:
        with (OUTPUT_DIR / "dual_window_recheck_real.csv").open(
            "w", newline=""
        ) as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=["case", "origin_date", "era", "skill"],
                lineterminator="\n",
            )
            writer.writeheader()
            for row in all_rows:
                writer.writerow({**row, "skill": f"{row['skill']:.6f}"})

    (OUTPUT_DIR / "dual_window_recheck.md").write_text(
        "\n".join(summary_lines).rstrip() + "\n"
    )
    print("\n".join(summary_lines))


if __name__ == "__main__":
    main()
