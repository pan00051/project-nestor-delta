#!/usr/bin/env python3
"""Build an expanded exploratory Spain case from Eurostat JSON-stat snapshots."""

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
BASE_CASE = ROOT / "cases" / "spain_retail_eurostat_2008_2025"
CASE_NAME = "spain_retail_eurostat_expanded_2008_2025"
OUTPUT_DIR = ROOT / "cases" / CASE_NAME
REPORT_DIR = ROOT / "reports" / CASE_NAME
START = "2008-01"
END = "2025-12"
EUROSTAT_API = (
    "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data"
)


@dataclass(frozen=True)
class SeriesSpec:
    name: str
    dataset: str
    filters: Tuple[Tuple[str, str], ...]


SERIES = (
    SeriesSpec(
        "industry_confidence",
        "ei_bssi_m_r2",
        (("freq", "M"), ("indic", "BS-ICI-BAL"), ("s_adj", "SA"), ("geo", "ES")),
    ),
    SeriesSpec(
        "construction_confidence",
        "ei_bssi_m_r2",
        (("freq", "M"), ("indic", "BS-CCI-BAL"), ("s_adj", "SA"), ("geo", "ES")),
    ),
    SeriesSpec(
        "economic_sentiment",
        "ei_bssi_m_r2",
        (("freq", "M"), ("indic", "BS-ESI-I"), ("s_adj", "SA"), ("geo", "ES")),
    ),
    SeriesSpec(
        "employment_expectations",
        "ei_bsee_m_r2",
        (
            ("freq", "M"),
            ("indic", "BS-EEI-I"),
            ("s_adj", "SA"),
            ("unit", "INX"),
            ("geo", "ES"),
        ),
    ),
    SeriesSpec(
        "industry_employment_expectations",
        "ei_bsee_m_r2",
        (
            ("freq", "M"),
            ("indic", "BS-IEME-BAL"),
            ("s_adj", "SA"),
            ("unit", "BAL"),
            ("geo", "ES"),
        ),
    ),
    SeriesSpec(
        "construction_production",
        "sts_copr_m",
        (
            ("freq", "M"),
            ("indic_bt", "PRD"),
            ("nace_r2", "F"),
            ("s_adj", "SCA"),
            ("unit", "I21"),
            ("geo", "ES"),
        ),
    ),
    SeriesSpec(
        "retail_employment",
        "sts_trlb_m",
        (
            ("freq", "M"),
            ("indic_bt", "EMP"),
            ("nace_r2", "G47"),
            ("s_adj", "SCA"),
            ("unit", "I21"),
            ("geo", "ES"),
        ),
    ),
    SeriesSpec(
        "industrial_turnover",
        "sts_intv_m",
        (
            ("freq", "M"),
            ("indic_bt", "NETTUR"),
            ("nace_r2", "B_C"),
            ("s_adj", "SCA"),
            ("unit", "I21"),
            ("geo", "ES"),
        ),
    ),
)


def _request_url(dataset: str) -> str:
    query = urllib.parse.urlencode(
        {
            "lang": "en",
            "freq": "M",
            "geo": "ES",
            "sinceTimePeriod": START,
            "untilTimePeriod": END,
        }
    )
    return f"{EUROSTAT_API}/{dataset}?{query}"


def _load_snapshot(
    dataset: str, snapshot_dir: Optional[Path]
) -> Mapping[str, object]:
    if snapshot_dir is not None:
        path = snapshot_dir / f"{dataset}.json"
        with path.open(encoding="utf-8") as handle:
            return json.load(handle)
    request = urllib.request.Request(
        _request_url(dataset), headers={"User-Agent": "Nestor-Delta-Case-Builder/1.0"}
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        return json.load(response)


def _category_position(dataset: Mapping[str, object], dimension: str, code: str) -> int:
    dimensions = dataset["dimension"]
    assert isinstance(dimensions, dict)
    category = dimensions[dimension]["category"]
    return int(category["index"][code])


def _extract_series(
    dataset: Mapping[str, object], spec: SeriesSpec
) -> Tuple[Tuple[str, float], ...]:
    dimension_ids = list(dataset["id"])
    sizes = [int(value) for value in dataset["size"]]
    strides = [math.prod(sizes[index + 1 :]) for index in range(len(sizes))]
    selected = {
        dimension: _category_position(dataset, dimension, code)
        for dimension, code in spec.filters
    }
    dimensions = dataset["dimension"]
    time_index = dimensions["time"]["category"]["index"]
    times = sorted(time_index.items(), key=lambda item: int(item[1]))
    values = dataset["value"]
    output: List[Tuple[str, float]] = []
    for date, time_position in times:
        positions = [
            int(time_position) if dimension == "time" else selected[dimension]
            for dimension in dimension_ids
        ]
        flat_index = sum(
            position * stride for position, stride in zip(positions, strides)
        )
        if isinstance(values, dict):
            value = values.get(str(flat_index))
        else:
            value = values[flat_index]
        if value is None:
            raise ValueError(f"{spec.name} is missing {date}")
        output.append((str(date), float(value)))
    if len(output) != 216 or output[0][0] != START or output[-1][0] != END:
        raise ValueError(f"{spec.name} does not cover the frozen 216-month axis")
    return tuple(output)


def _read_base_rows() -> Tuple[List[str], List[Dict[str, str]]]:
    with (BASE_CASE / "data.csv").open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        if reader.fieldnames is None:
            raise ValueError("base case has no header")
        return list(reader.fieldnames), rows


def _write_case(
    base_fields: Sequence[str],
    base_rows: Sequence[Mapping[str, str]],
    extracted: Mapping[str, Tuple[Tuple[str, float], ...]],
    metadata: Mapping[str, Mapping[str, str]],
) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    fields = list(base_fields) + [spec.name for spec in SERIES]
    by_name = {
        name: dict(rows) for name, rows in extracted.items()
    }
    csv_path = OUTPUT_DIR / "data.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for base_row in base_rows:
            date = base_row["date"]
            row = dict(base_row)
            for spec in SERIES:
                row[spec.name] = f"{by_name[spec.name][date]:.10f}"
            writer.writerow(row)

    digest = hashlib.sha256(csv_path.read_bytes()).hexdigest()
    candidates = [field for field in base_fields if field not in {"date", "retail_volume"}]
    candidates.extend(spec.name for spec in SERIES)
    config = {
        "candidate_signals": candidates,
        "case_name": CASE_NAME,
        "csv": "data.csv",
        "date_column": "date",
        "frequency": "monthly",
        "lag_window": 2,
        "max_selected_signals": 12,
        "notes": (
            "Exploratory expansion of the frozen Eurostat Spain retail case. "
            "Eight additional monthly Spain series were fixed before this run; all "
            "cover 2008-01 through 2025-12 with no deletion, interpolation, or "
            "imputation. The 2024-2025 test period was already observed in the "
            "original case, so any improvement here is exploratory and requires a "
            "new untouched period for confirmation. Results describe co-movement "
            "and out-of-sample predictive usefulness, not causation. Clean CSV "
            f"SHA-256: {digest}."
        ),
        "output_dir": f"../../reports/{CASE_NAME}",
        "seasonal_period": 0,
        "target": "retail_volume",
        "test_start": "2024-01",
        "train_end": "2023-12",
    }
    (OUTPUT_DIR / "case.json").write_text(
        json.dumps(config, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    manifest = {
        "base_case": str(BASE_CASE.relative_to(ROOT)),
        "clean_csv_sha256": digest,
        "decision_boundary": (
            "Candidate pool, lag_window=2, max_selected_signals=12, and all five "
            "budget tiers were fixed before evaluating the expanded case."
        ),
        "experiment_status": (
            "Exploratory: the 2024-2025 evaluation period was seen in the prior case."
        ),
        "missing_value_policy": "Reject any missing month; no filling or interpolation.",
        "series": [metadata[spec.name] for spec in SERIES],
    }
    (OUTPUT_DIR / "source_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--snapshot-dir",
        type=Path,
        help="Read <dataset>.json snapshots from this directory instead of the API.",
    )
    args = parser.parse_args()

    datasets: Dict[str, Mapping[str, object]] = {}
    for dataset_name in sorted({spec.dataset for spec in SERIES}):
        datasets[dataset_name] = _load_snapshot(dataset_name, args.snapshot_dir)

    extracted: Dict[str, Tuple[Tuple[str, float], ...]] = {}
    metadata: Dict[str, Mapping[str, str]] = {}
    for spec in SERIES:
        dataset = datasets[spec.dataset]
        extracted[spec.name] = _extract_series(dataset, spec)
        metadata[spec.name] = {
            "dataset": spec.dataset,
            "filters": "&".join(f"{key}={value}" for key, value in spec.filters),
            "name": spec.name,
            "source_url": _request_url(spec.dataset),
            "updated": str(dataset.get("updated", "")),
        }

    base_fields, base_rows = _read_base_rows()
    _write_case(base_fields, base_rows, extracted, metadata)
    print(f"Wrote {OUTPUT_DIR / 'data.csv'}")
    print(f"Wrote {OUTPUT_DIR / 'case.json'}")
    print(f"Wrote {OUTPUT_DIR / 'source_manifest.json'}")
    print(f"Reports will be written to {REPORT_DIR}")


if __name__ == "__main__":
    main()
