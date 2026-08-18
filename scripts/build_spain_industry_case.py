#!/usr/bin/env python3
"""Build the Spain industrial-production case with explicit scope substitutions."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Tuple


ROOT = Path(__file__).resolve().parents[1]
CASE_NAME = "spain_industrial_production_eurostat_2008_2023"
CASE_DIR = ROOT / "cases" / CASE_NAME
START = "2008-01"
END = "2023-12"
API_ROOT = (
    "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data"
)


@dataclass(frozen=True)
class SeriesSpec:
    name: str
    dataset: str
    actual_filters: Tuple[Tuple[str, str], ...]
    requested_scope: str
    actual_scope: str
    semantic_difference: str


SERIES = (
    SeriesSpec(
        "industrial_production",
        "sts_inpr_m",
        (
            ("freq", "M"),
            ("nace_r2", "C"),
            ("s_adj", "SCA"),
            ("unit", "I15"),
            ("geo", "ES"),
        ),
        "sts_inpr_m; nace_r2=C; s_adj=SCA; unit=I15; geo=ES",
        "sts_inpr_m; nace_r2=C; s_adj=SCA; unit=I15; geo=ES",
        "No substitution. This is the target manufacturing production volume index.",
    ),
    SeriesSpec(
        "order_book_assessment",
        "ei_bsin_m_r2",
        (
            ("freq", "M"),
            ("indic", "BS-IOB"),
            ("s_adj", "SA"),
            ("unit", "BAL"),
            ("geo", "ES"),
        ),
        "sts_inot_m; nace_r2=C; s_adj=SCA; unit=I15; geo=ES",
        "ei_bsin_m_r2; indic=BS-IOB; s_adj=SA; unit=BAL; geo=ES",
        (
            "SUBSTANTIVE CHANGE: the requested series was a quantitative index of "
            "actual industrial new orders. The used series is a seasonally adjusted "
            "survey balance of managers' assessment of current order-book levels. "
            "It measures sentiment about order books, not the quantity of new orders, "
            "and must not be interpreted as an equivalent replacement."
        ),
    ),
    SeriesSpec(
        "production_expectations",
        "ei_bsin_m_r2",
        (
            ("freq", "M"),
            ("indic", "BS-IPE"),
            ("s_adj", "SA"),
            ("unit", "BAL"),
            ("geo", "ES"),
        ),
        "ei_bsin_m_r2; indic=BS-IND-PO; s_adj=SA; geo=ES",
        "ei_bsin_m_r2; indic=BS-IPE; s_adj=SA; unit=BAL; geo=ES",
        (
            "The requested indicator code is not present in the current dataset. "
            "BS-IPE is the current Eurostat code for production expectations over "
            "the next three months."
        ),
    ),
    SeriesSpec(
        "domestic_energy_producer_prices",
        "sts_inppd_m",
        (
            ("freq", "M"),
            ("nace_r2", "MIG_NRG"),
            ("s_adj", "NSA"),
            ("unit", "I15"),
            ("geo", "ES"),
        ),
        "sts_inppd_m; nace_r2=C19-C20; s_adj=NSA; unit=I15; geo=ES",
        "sts_inppd_m; nace_r2=MIG_NRG; s_adj=NSA; unit=I15; geo=ES",
        (
            "C19-C20 is not a current NACE aggregate in this dataset. MIG_NRG is "
            "the available Main Industrial Grouping for energy and is broader than "
            "a simple combination of coke/refined petroleum and chemicals."
        ),
    ),
    SeriesSpec(
        "manufacturing_employment_expectations",
        "ei_bsin_m_r2",
        (
            ("freq", "M"),
            ("indic", "BS-IEME-BAL"),
            ("s_adj", "SA"),
            ("unit", "BAL"),
            ("geo", "ES"),
        ),
        "ei_bsin_m_r2; indic=BS-IND-EMPE; s_adj=SA; geo=ES",
        "ei_bsin_m_r2; indic=BS-IEME-BAL; s_adj=SA; unit=BAL; geo=ES",
        (
            "The requested indicator code is not present in the current dataset. "
            "BS-IEME-BAL is the current industry employment-expectations balance "
            "for the next three months."
        ),
    ),
)


def _url(spec: SeriesSpec) -> str:
    query: List[Tuple[str, str]] = [("lang", "en")]
    query.extend(spec.actual_filters)
    query.extend(
        (("sinceTimePeriod", START), ("untilTimePeriod", END))
    )
    return f"{API_ROOT}/{spec.dataset}?{urllib.parse.urlencode(query)}"


def _load_dataset(
    spec: SeriesSpec, snapshot_dir: Optional[Path]
) -> Mapping[str, object]:
    if snapshot_dir is not None:
        path = snapshot_dir / f"{spec.dataset}.json"
        with path.open(encoding="utf-8") as handle:
            return json.load(handle)
    request = urllib.request.Request(
        _url(spec), headers={"User-Agent": "Nestor-Delta-Case-Builder/1.0"}
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        return json.load(response)


def _position(dataset: Mapping[str, object], dimension: str, code: str) -> int:
    dimensions = dataset["dimension"]
    assert isinstance(dimensions, dict)
    try:
        return int(dimensions[dimension]["category"]["index"][code])
    except KeyError as error:
        raise ValueError(f"missing dimension code {dimension}={code}") from error


def _extract(
    dataset: Mapping[str, object], spec: SeriesSpec
) -> Tuple[Tuple[str, float], ...]:
    ids = list(dataset["id"])
    sizes = [int(value) for value in dataset["size"]]
    strides = [math.prod(sizes[index + 1 :]) for index in range(len(sizes))]
    selected = {
        dimension: _position(dataset, dimension, code)
        for dimension, code in spec.actual_filters
    }
    for dimension, size in zip(ids, sizes):
        if dimension == "time" or dimension in selected:
            continue
        if size != 1:
            raise ValueError(
                f"{spec.name} leaves non-singleton dimension {dimension} unspecified"
            )
        selected[dimension] = 0
    dimensions = dataset["dimension"]
    time_index = dimensions["time"]["category"]["index"]
    times = sorted(time_index.items(), key=lambda item: int(item[1]))
    values = dataset["value"]
    output: List[Tuple[str, float]] = []
    for date, time_position in times:
        positions = [
            int(time_position) if dimension == "time" else selected[dimension]
            for dimension in ids
        ]
        flat_index = sum(
            position * stride for position, stride in zip(positions, strides)
        )
        if isinstance(values, dict):
            value = values.get(str(flat_index))
        else:
            value = values[flat_index]
        if value is None:
            raise ValueError(f"{spec.name} is missing {date}; no filling is allowed")
        output.append((str(date), float(value)))
    if len(output) != 192 or output[0][0] != START or output[-1][0] != END:
        raise ValueError(f"{spec.name} does not cover the exact 192-month axis")
    return tuple(output)


def _write_data(extracted: Mapping[str, Sequence[Tuple[str, float]]]) -> str:
    CASE_DIR.mkdir(parents=True, exist_ok=True)
    dates = [date for date, _ in extracted[SERIES[0].name]]
    values_by_name = {
        name: dict(values) for name, values in extracted.items()
    }
    fieldnames = ["date"] + [spec.name for spec in SERIES]
    path = CASE_DIR / "data.csv"
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for date in dates:
            writer.writerow(
                {
                    "date": date,
                    **{
                        spec.name: f"{values_by_name[spec.name][date]:.10f}"
                        for spec in SERIES
                    },
                }
            )
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_config(digest: str) -> None:
    config = {
        "candidate_signals": [spec.name for spec in SERIES[1:]],
        "case_name": CASE_NAME,
        "csv": "data.csv",
        "date_column": "date",
        "frequency": "monthly",
        "lag_window": 3,
        "max_selected_signals": 3,
        "notes": (
            "Eurostat Spain monthly manufacturing case, 2008-01 through 2023-12, "
            "with an exact 192-month axis and no deletion, interpolation, or "
            "imputation. The original request used unavailable or obsolete codes for "
            "four candidate scopes. The actual scopes and semantic differences are "
            "recorded in methodology.md and source_manifest.json. In particular, "
            "order_book_assessment is a qualitative survey balance, not the requested "
            "quantitative industrial new-orders index. Results describe co-movement "
            "and out-of-sample predictive usefulness only, not causation. Clean CSV "
            f"SHA-256: {digest}."
        ),
        "output_dir": f"../../reports/{CASE_NAME}",
        "seasonal_period": 0,
        "target": "industrial_production",
        "test_start": "2022-01",
        "train_end": "2021-12",
    }
    (CASE_DIR / "case.json").write_text(
        json.dumps(config, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def _write_documentation(
    datasets: Mapping[str, Mapping[str, object]], digest: str
) -> None:
    rows = []
    for spec in SERIES:
        dataset = datasets[spec.name]
        rows.append(
            {
                "actual_scope": spec.actual_scope,
                "dataset_updated": str(dataset.get("updated", "")),
                "name": spec.name,
                "requested_scope": spec.requested_scope,
                "semantic_difference": spec.semantic_difference,
                "source_url": _url(spec),
            }
        )
    manifest = {
        "case_name": CASE_NAME,
        "clean_csv_sha256": digest,
        "coverage": {"end": END, "frequency": "monthly", "months": 192, "start": START},
        "honesty_boundary": (
            "Requested and actual scopes are not silently treated as equivalent. "
            "The order-book survey substitution is a substantive semantic change."
        ),
        "missing_value_policy": "Reject any missing month; no filling or interpolation.",
        "series": rows,
    }
    (CASE_DIR / "source_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    lines = [
        "# Data Scope and Honesty Boundary",
        "",
        "This case uses an exact monthly axis from `2008-01` through `2023-12`",
        "(192 months). No rows were deleted and no values were filled or interpolated.",
        "",
        "The original request contained dataset or dimension codes that are unavailable",
        "in the current Eurostat API. The substitutions below are explicit and must not",
        "be read as silent equivalence.",
        "",
        "| Role | Original requested scope | Actual scope used | Semantic boundary |",
        "|---|---|---|---|",
    ]
    roles = ["Target", "Signal 1", "Signal 2", "Signal 3", "Signal 4"]
    for role, spec in zip(roles, SERIES):
        difference = spec.semantic_difference.replace("|", "\\|")
        lines.append(
            f"| {role} | `{spec.requested_scope}` | `{spec.actual_scope}` | {difference} |"
        )
    lines.extend(
        [
            "",
            "## Critical Difference: New Orders vs Order-Book Assessment",
            "",
            "The originally requested industrial new-orders series was a quantitative",
            "index intended to represent actual new-order volume. The actual",
            "`BS-IOB` series is a qualitative, seasonally adjusted survey balance: it",
            "summarises managers' assessments of current order-book levels. It does not",
            "measure the quantity of newly received orders. Any result involving this",
            "signal must therefore be described as association with reported order-book",
            "sentiment, not association with actual new-order volume.",
            "",
            "This distinction is part of Delta's honesty boundary and must remain visible",
            "in reports or portfolio material derived from this case.",
            "",
        ]
    )
    (CASE_DIR / "methodology.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--snapshot-dir",
        type=Path,
        help="Read <dataset>.json snapshots from this directory instead of the API.",
    )
    args = parser.parse_args()

    datasets: Dict[str, Mapping[str, object]] = {}
    extracted: Dict[str, Tuple[Tuple[str, float], ...]] = {}
    for spec in SERIES:
        dataset = _load_dataset(spec, args.snapshot_dir)
        datasets[spec.name] = dataset
        extracted[spec.name] = _extract(dataset, spec)

    digest = _write_data(extracted)
    _write_config(digest)
    _write_documentation(datasets, digest)
    for name in ("data.csv", "case.json", "source_manifest.json", "methodology.md"):
        print(f"Wrote {CASE_DIR / name}")


if __name__ == "__main__":
    main()
