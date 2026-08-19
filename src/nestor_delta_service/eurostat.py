"""Eurostat JSON-stat intake for the website service adapter."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

API_ROOT = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data"
USER_AGENT = "Nestor-Delta-Website-Adapter/0.1"


@dataclass(frozen=True)
class EurostatSeriesSpec:
    name: str
    dataset: str
    filters: tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class EurostatSnapshot:
    dates: tuple[str, ...]
    rows: tuple[Mapping[str, float], ...]
    signal_metadata: Mapping[str, Mapping[str, Any]]
    snapshot_hash: str
    provenance: Mapping[str, Any]
    csv_text: str


def build_eurostat_snapshot(payload: Mapping[str, Any]) -> EurostatSnapshot:
    """Fetch or read Eurostat JSON-stat payloads and align them into one snapshot."""
    start = str(payload.get("start") or "")
    end = str(payload.get("end") or "")
    if not start or not end:
        raise ValueError("eurostat.start and eurostat.end are required")
    specs = _series_specs(payload.get("series"))
    snapshots = payload.get("snapshots") or {}
    if not isinstance(snapshots, Mapping):
        raise ValueError("eurostat.snapshots must be an object when provided")

    extracted = {}
    metadata = {}
    provenance_series = []
    for spec in specs:
        dataset_payload = snapshots.get(spec.name) or snapshots.get(spec.dataset)
        if dataset_payload is None:
            dataset_payload = fetch_eurostat_json(spec, start, end)
        elif isinstance(dataset_payload, str):
            dataset_payload = json.loads(dataset_payload)
        if not isinstance(dataset_payload, Mapping):
            raise ValueError(f"snapshot for {spec.name!r} must be a JSON object")
        values = extract_jsonstat_series(dataset_payload, spec)
        dates = tuple(date for date, _ in values)
        if dates != _month_axis(start, end):
            raise ValueError(
                f"{spec.name} does not cover the exact {start}..{end} monthly axis"
            )
        extracted[spec.name] = dict(values)
        scope = dict(spec.filters)
        coverage = {"start": start, "end": end, "months": len(dates)}
        metadata[spec.name] = {
            "unit": scope.get("unit", "unknown"),
            "seasonal_adjustment": scope.get("s_adj", "unknown"),
            "coverage": coverage,
        }
        provenance_series.append(
            {
                "name": spec.name,
                "dataset": spec.dataset,
                "filters": scope,
                "source_url": eurostat_url(spec, start, end),
                "updated": str(dataset_payload.get("updated", "")),
            }
        )

    dates = _month_axis(start, end)
    rows = tuple(
        {spec.name: float(extracted[spec.name][date]) for spec in specs}
        for date in dates
    )
    csv_text = _snapshot_csv(dates, specs, rows)
    digest = hashlib.sha256(csv_text.encode("utf-8")).hexdigest()
    return EurostatSnapshot(
        dates=dates,
        rows=rows,
        signal_metadata=metadata,
        snapshot_hash=digest,
        provenance={
            "source": "eurostat",
            "coverage": {"start": start, "end": end, "months": len(dates)},
            "series": provenance_series,
            "missing_value_policy": "Reject any missing month; no filling or interpolation.",
        },
        csv_text=csv_text,
    )


def fetch_eurostat_json(
    spec: EurostatSeriesSpec,
    start: str,
    end: str,
    *,
    timeout_seconds: int = 120,
) -> Mapping[str, Any]:
    request = urllib.request.Request(
        eurostat_url(spec, start, end),
        headers={"User-Agent": USER_AGENT},
    )
    with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
        payload = json.load(response)
    if not isinstance(payload, Mapping):
        raise ValueError(f"Eurostat response for {spec.name!r} must be a JSON object")
    return payload


def eurostat_url(spec: EurostatSeriesSpec, start: str, end: str) -> str:
    query = [("lang", "en")]
    query.extend(spec.filters)
    query.extend((("sinceTimePeriod", start), ("untilTimePeriod", end)))
    return f"{API_ROOT}/{spec.dataset}?{urllib.parse.urlencode(query)}"


def extract_jsonstat_series(
    dataset: Mapping[str, Any],
    spec: EurostatSeriesSpec,
) -> tuple[tuple[str, float], ...]:
    ids = tuple(str(value) for value in dataset["id"])
    sizes = tuple(int(value) for value in dataset["size"])
    if len(ids) != len(sizes):
        raise ValueError(f"{spec.name} JSON-stat id/size dimensions do not match")
    strides = tuple(math.prod(sizes[index + 1 :]) for index in range(len(sizes)))
    selected = {
        dimension: _category_position(dataset, dimension, code)
        for dimension, code in spec.filters
    }
    for dimension, size in zip(ids, sizes):
        if dimension == "time" or dimension in selected:
            continue
        if size != 1:
            raise ValueError(
                f"{spec.name} leaves non-singleton dimension {dimension} unspecified"
            )
        selected[dimension] = 0
    time_index = dataset["dimension"]["time"]["category"]["index"]
    times = sorted(time_index.items(), key=lambda item: int(item[1]))
    values = dataset["value"]
    output = []
    for date, time_position in times:
        positions = [
            int(time_position) if dimension == "time" else selected[dimension]
            for dimension in ids
        ]
        flat_index = sum(
            position * stride for position, stride in zip(positions, strides)
        )
        value = values.get(str(flat_index)) if isinstance(values, Mapping) else values[flat_index]
        if value is None:
            raise ValueError(f"{spec.name} is missing {date}; no filling is allowed")
        output.append((str(date), float(value)))
    return tuple(output)


def _series_specs(raw: Any) -> tuple[EurostatSeriesSpec, ...]:
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)) or not raw:
        raise ValueError("eurostat.series must be a non-empty list")
    specs = []
    names = set()
    for item in raw:
        if not isinstance(item, Mapping):
            raise ValueError("each eurostat series must be an object")
        name = str(item.get("name") or "")
        dataset = str(item.get("dataset") or "")
        filters = item.get("filters")
        if not name or not dataset:
            raise ValueError("each eurostat series requires name and dataset")
        if name in names:
            raise ValueError(f"duplicate eurostat series name: {name}")
        if not isinstance(filters, Mapping):
            raise ValueError(f"eurostat series {name!r} requires filters object")
        specs.append(
            EurostatSeriesSpec(
                name=name,
                dataset=dataset,
                filters=tuple((str(key), str(value)) for key, value in filters.items()),
            )
        )
        names.add(name)
    return tuple(specs)


def _category_position(dataset: Mapping[str, Any], dimension: str, code: str) -> int:
    try:
        index = dataset["dimension"][dimension]["category"]["index"][code]
    except KeyError as exc:
        raise ValueError(f"missing dimension code {dimension}={code}") from exc
    return int(index)


def _month_axis(start: str, end: str) -> tuple[str, ...]:
    start_index = _parse_month(start)
    end_index = _parse_month(end)
    if end_index < start_index:
        raise ValueError("eurostat.end must not be earlier than eurostat.start")
    return tuple(_month_label(index) for index in range(start_index, end_index + 1))


def _snapshot_csv(
    dates: Sequence[str],
    specs: Sequence[EurostatSeriesSpec],
    rows: Sequence[Mapping[str, float]],
) -> str:
    handle = io.StringIO()
    fieldnames = ["date"] + [spec.name for spec in specs]
    writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()
    for date, row in zip(dates, rows):
        writer.writerow(
            {
                "date": date,
                **{spec.name: f"{float(row[spec.name]):.10f}" for spec in specs},
            }
        )
    return handle.getvalue()


def _parse_month(value: str) -> int:
    parts = value.split("-")
    if len(parts) != 2 or len(parts[0]) != 4 or len(parts[1]) != 2:
        raise ValueError("Eurostat dates must use YYYY-MM format")
    year = int(parts[0])
    month = int(parts[1])
    if not 1 <= month <= 12:
        raise ValueError("Eurostat month must be between 01 and 12")
    return year * 12 + month


def _month_label(month_index: int) -> str:
    year = (month_index - 1) // 12
    month = (month_index - 1) % 12 + 1
    return f"{year:04d}-{month:02d}"
