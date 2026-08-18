#!/usr/bin/env python3
"""Build corrected 15-signal Spain cases for validation-first experiments."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Tuple


ROOT = Path(__file__).resolve().parents[1]
RETAIL_CASE = ROOT / "cases" / "spain_retail_eurostat_expanded_2008_2025"
INDUSTRY_CASE = ROOT / "cases" / "spain_industrial_production_eurostat_2008_2023"
REPORT_DIR = ROOT / "reports" / "spain_industrial_production_dual_window"
START = "2008-01"
END = "2021-12"
API_ROOT = (
    "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data"
)

TARGET = "industrial_production"
CANDIDATES = (
    "unemployment_rate",
    "consumer_confidence",
    "hicp",
    "industry_confidence",
    "construction_confidence",
    "economic_sentiment",
    "employment_expectations",
    "industry_employment_expectations",
    "construction_production",
    "retail_employment",
    "industrial_turnover",
    "order_book_assessment",
    "production_expectations",
    "domestic_energy_producer_prices",
    "services_confidence",
)

CASE_SPECS = (
    {
        "case_name": "spain_industrial_normal_2008_2021",
        "train_start": "2008-01",
        "train_end": "2013-12",
        "validation_start": "2014-01",
        "validation_end": "2015-12",
        "test_start": "2016-01",
        "test_end": "2019-12",
    },
    {
        "case_name": "spain_industrial_shock_2008_2021",
        "train_start": "2008-01",
        "train_end": "2017-12",
        "validation_start": "2018-01",
        "validation_end": "2019-12",
        "test_start": "2020-01",
        "test_end": "2021-12",
    },
)


def _survey_url(indicator: str) -> str:
    query = urllib.parse.urlencode(
        {
            "lang": "en",
            "freq": "M",
            "indic": indicator,
            "s_adj": "SA",
            "geo": "ES",
            "sinceTimePeriod": START,
            "untilTimePeriod": END,
        }
    )
    return f"{API_ROOT}/ei_bssi_m_r2?{query}"


def _load_survey(indicator: str, snapshot: Optional[Path]) -> Mapping[str, object]:
    if snapshot is not None:
        with snapshot.open(encoding="utf-8") as handle:
            return json.load(handle)
    request = urllib.request.Request(
        _survey_url(indicator),
        headers={"User-Agent": "Nestor-Delta-Case-Builder/1.0"},
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        return json.load(response)


def _extract_single_series(
    dataset: Mapping[str, object], name: str
) -> Tuple[Tuple[str, float], ...]:
    ids = list(dataset["id"])
    sizes = [int(value) for value in dataset["size"]]
    if any(size != 1 for dimension, size in zip(ids, sizes) if dimension != "time"):
        raise ValueError(f"{name} snapshot must contain exactly one series")
    strides = [math.prod(sizes[index + 1 :]) for index in range(len(sizes))]
    dimensions = dataset["dimension"]
    times = sorted(
        dimensions["time"]["category"]["index"].items(),
        key=lambda item: int(item[1]),
    )
    values = dataset["value"]
    output: List[Tuple[str, float]] = []
    for date, time_position in times:
        positions = [int(time_position) if dimension == "time" else 0 for dimension in ids]
        flat_index = sum(
            position * stride for position, stride in zip(positions, strides)
        )
        if isinstance(values, dict):
            value = values.get(str(flat_index))
        else:
            value = values[flat_index]
        if value is None:
            raise ValueError(f"{name} is missing {date}; filling is forbidden")
        output.append((str(date), float(value)))
    if len(output) != 168 or output[0][0] != START or output[-1][0] != END:
        raise ValueError(f"{name} does not cover the exact 168-month axis")
    return tuple(output)


def _read_rows(path: Path) -> Dict[str, Dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return {
            row["date"]: row
            for row in csv.DictReader(handle)
            if START <= row["date"] <= END
        }


def _series_hash(values: Sequence[float]) -> str:
    payload = "".join(f"{value:.10f}\n" for value in values).encode("ascii")
    return hashlib.sha256(payload).hexdigest()


def _build_rows(
    consumer: Mapping[str, float], services: Mapping[str, float]
) -> Tuple[Tuple[Dict[str, float], ...], Tuple[Dict[str, object], ...]]:
    retail = _read_rows(RETAIL_CASE / "data.csv")
    industry = _read_rows(INDUSTRY_CASE / "data.csv")
    dates = tuple(sorted(retail))
    if dates != tuple(sorted(industry)) or len(dates) != 168:
        raise ValueError("source cases do not share the exact 168-month axis")

    rows: List[Dict[str, float]] = []
    for date in dates:
        row = {"date": date, TARGET: float(industry[date][TARGET])}
        for name in CANDIDATES:
            if name == "consumer_confidence":
                value = consumer[date]
            elif name == "services_confidence":
                value = services[date]
            elif name in retail[date]:
                value = float(retail[date][name])
            else:
                value = float(industry[date][name])
            row[name] = float(value)
        rows.append(row)

    hash_rows: List[Dict[str, object]] = []
    seen: Dict[str, str] = {}
    for name in CANDIDATES:
        values = [float(row[name]) for row in rows]
        if len(values) != 168:
            raise ValueError(f"{name} does not contain 168 values")
        digest = _series_hash(values)
        duplicate_of = seen.get(digest, "")
        hash_rows.append(
            {
                "signal": name,
                "month_count": 168,
                "missing_count": 0,
                "sha256": digest,
                "duplicate_of": duplicate_of,
                "gate_status": "PASS" if not duplicate_of else "FAIL_DUPLICATE",
            }
        )
        seen[digest] = name
    if any(row["gate_status"] != "PASS" for row in hash_rows):
        raise ValueError("candidate SHA-256 gate found a duplicate")
    return tuple(rows), tuple(hash_rows)


def _write_gate(rows: Sequence[Mapping[str, object]]) -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    path = REPORT_DIR / "availability_gate.csv"
    fields = [
        "signal",
        "month_count",
        "missing_count",
        "sha256",
        "duplicate_of",
        "gate_status",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _write_case(case_spec: Mapping[str, str], rows: Sequence[Mapping[str, float]]) -> None:
    case_dir = ROOT / "cases" / case_spec["case_name"]
    case_dir.mkdir(parents=True, exist_ok=True)
    fields = ["date", TARGET] + list(CANDIDATES)
    data_path = case_dir / "data.csv"
    with data_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "date": row["date"],
                    **{name: f"{float(row[name]):.10f}" for name in fields[1:]},
                }
            )
    digest = hashlib.sha256(data_path.read_bytes()).hexdigest()
    payload = {
        **case_spec,
        "candidate_signals": list(CANDIDATES),
        "csv": "data.csv",
        "date_column": "date",
        "frequency": "monthly",
        "lag_windows": [1, 2, 3, 4, 5, 6],
        "max_selected_signals": [1, 2, 3, 4, 5],
        "notes": (
            "Validation-only adaptive parameter search. The true consumer confidence "
            "series BS-CSMCI-BAL replaces the mislabeled frozen retail-case column; "
            "services confidence BS-SCI-BAL is the fifteenth unique signal. Test data "
            "must not be evaluated until validation selection receives author approval. "
            f"Clean CSV SHA-256: {digest}."
        ),
        "output_dir": f"../../reports/{case_spec['case_name']}",
        "relation_thresholds": [0.06, 0.17, 0.28, 0.39, 0.50],
        "target": TARGET,
    }
    (case_dir / "adaptive_case.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--consumer-snapshot", type=Path)
    parser.add_argument("--services-snapshot", type=Path)
    args = parser.parse_args()

    consumer_dataset = _load_survey("BS-CSMCI-BAL", args.consumer_snapshot)
    services_dataset = _load_survey("BS-SCI-BAL", args.services_snapshot)
    consumer = dict(_extract_single_series(consumer_dataset, "consumer_confidence"))
    services = dict(_extract_single_series(services_dataset, "services_confidence"))
    rows, gate_rows = _build_rows(consumer, services)
    _write_gate(gate_rows)
    for case_spec in CASE_SPECS:
        _write_case(case_spec, rows)
    print(f"Wrote {REPORT_DIR / 'availability_gate.csv'}")
    for case_spec in CASE_SPECS:
        print(f"Wrote cases/{case_spec['case_name']}/data.csv")
        print(f"Wrote cases/{case_spec['case_name']}/adaptive_case.json")


if __name__ == "__main__":
    main()
