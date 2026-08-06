"""Config-driven real-data case loading for Sprint 6."""

from __future__ import annotations

import csv
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

from .synthetic import Row


@dataclass(frozen=True)
class RealCaseConfig:
    """A narrow real-data case spec for author-prepared CSV files."""

    case_name: str
    csv_path: Path
    date_column: str
    target: str
    candidate_signals: Tuple[str, ...]
    frequency: str
    lag_window: int
    train_end: str
    test_start: str
    max_selected_signals: int
    output_dir: Path
    seasonal_period: int = 0
    notes: str = ""


@dataclass(frozen=True)
class RealCaseData:
    """Validated numeric rows plus aligned date labels."""

    dates: Tuple[str, ...]
    rows: Tuple[Row, ...]
    variables: Tuple[str, ...]


REQUIRED_CONFIG_FIELDS = {
    "case_name",
    "csv",
    "date_column",
    "target",
    "candidate_signals",
    "frequency",
    "lag_window",
    "train_end",
    "test_start",
    "max_selected_signals",
    "output_dir",
    "seasonal_period",
    "notes",
}


def load_real_case_config(path: Path) -> RealCaseConfig:
    """Load a case config from JSON without interpreting external services."""
    root = path.resolve().parent
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("case config must be a JSON object")

    payload_keys = set(payload)
    missing = sorted(REQUIRED_CONFIG_FIELDS - payload_keys)
    extra = sorted(payload_keys - REQUIRED_CONFIG_FIELDS)
    if missing:
        raise ValueError(f"case config missing required fields: {missing}")
    if extra:
        raise ValueError(f"case config contains unknown fields: {extra}")
    _validate_config_types(payload)

    candidate_signals = tuple(payload["candidate_signals"])
    output_dir = Path(payload["output_dir"])
    if not output_dir.is_absolute():
        output_dir = root / output_dir

    csv_path = Path(payload["csv"])
    if not csv_path.is_absolute():
        csv_path = root / csv_path

    config = RealCaseConfig(
        case_name=str(payload["case_name"]),
        csv_path=csv_path,
        date_column=str(payload.get("date_column", "date")),
        target=str(payload["target"]),
        candidate_signals=candidate_signals,
        frequency=str(payload["frequency"]),
        lag_window=int(payload["lag_window"]),
        train_end=str(payload["train_end"]),
        test_start=str(payload["test_start"]),
        max_selected_signals=int(payload["max_selected_signals"]),
        output_dir=output_dir,
        seasonal_period=int(payload["seasonal_period"]),
        notes=str(payload["notes"]),
    )
    validate_real_case_config(config)
    return config


def validate_real_case_config(config: RealCaseConfig) -> None:
    if not config.case_name:
        raise ValueError("case_name must not be empty")
    if config.target in config.candidate_signals:
        raise ValueError("target must not also be a candidate signal")
    if len(set(config.candidate_signals)) != len(config.candidate_signals):
        raise ValueError("candidate_signals must be unique")
    if config.frequency != "monthly":
        raise ValueError("frequency must be 'monthly'")
    _parse_month(config.train_end, "train_end")
    _parse_month(config.test_start, "test_start")
    if config.lag_window < 1:
        raise ValueError("lag_window must be at least 1")
    if config.max_selected_signals < 1:
        raise ValueError("max_selected_signals must be at least 1")
    if config.max_selected_signals > len(config.candidate_signals):
        raise ValueError("max_selected_signals cannot exceed candidate count")
    if config.seasonal_period < 0:
        raise ValueError("seasonal_period cannot be negative")
    if config.train_end >= config.test_start:
        raise ValueError("train_end must be earlier than test_start")


def load_real_case_data(config: RealCaseConfig) -> RealCaseData:
    """Load author-prepared numeric CSV data in chronological order."""
    required_columns = (config.date_column, config.target) + config.candidate_signals
    rows_by_date: List[Tuple[str, Row]] = []

    with config.csv_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError("CSV must include a header row")
        missing = [column for column in required_columns if column not in reader.fieldnames]
        if missing:
            raise ValueError(f"CSV is missing required columns: {missing}")
        extra = [
            column
            for column in reader.fieldnames
            if column not in set(required_columns)
        ]
        if extra:
            raise ValueError(f"CSV contains unconfigured columns: {extra}")

        for index, record in enumerate(reader, start=2):
            date_value = str(record[config.date_column]).strip()
            if not date_value:
                raise ValueError(f"empty date at CSV row {index}")
            _parse_month(date_value, f"CSV row {index} date")
            numeric_row: Row = {}
            for column in (config.target,) + config.candidate_signals:
                try:
                    value = float(record[column])
                except ValueError as exc:
                    raise ValueError(
                        f"non-numeric value in column {column!r} at CSV row {index}"
                    ) from exc
                if not math.isfinite(value):
                    raise ValueError(
                        f"non-finite value in column {column!r} at CSV row {index}"
                    )
                numeric_row[column] = value
            rows_by_date.append((date_value, numeric_row))

    if len(rows_by_date) <= config.lag_window:
        raise ValueError("CSV must contain more rows than lag_window")

    dates = tuple(date for date, _ in rows_by_date)
    if len(set(dates)) != len(dates):
        raise ValueError("date values must be unique")
    _validate_monthly_sequence(dates)

    return RealCaseData(
        dates=dates,
        rows=tuple(row for _, row in rows_by_date),
        variables=(config.target,) + tuple(sorted(config.candidate_signals)),
    )


def real_case_label_rows(
    dates: Tuple[str, ...], config: RealCaseConfig
) -> Tuple[Tuple[int, ...], Tuple[int, ...]]:
    """Return train/test label indexes using only declared date boundaries."""
    train = tuple(
        index
        for index, date in enumerate(dates)
        if index >= config.lag_window and date <= config.train_end
    )
    test = tuple(
        index
        for index, date in enumerate(dates)
        if index >= config.lag_window and date >= config.test_start
    )
    if not train:
        raise ValueError("no train label rows after lag warm-up")
    if not test:
        raise ValueError("no test label rows after lag warm-up")
    return train, test


def _validate_config_types(payload: Dict[str, object]) -> None:
    string_fields = {
        "case_name",
        "csv",
        "date_column",
        "target",
        "frequency",
        "train_end",
        "test_start",
        "output_dir",
        "notes",
    }
    integer_fields = {"lag_window", "max_selected_signals", "seasonal_period"}
    for field in string_fields:
        if not isinstance(payload[field], str):
            raise ValueError(f"case config field {field!r} must be a string")
    for field in integer_fields:
        if not isinstance(payload[field], int):
            raise ValueError(f"case config field {field!r} must be an integer")
    if not isinstance(payload["candidate_signals"], list):
        raise ValueError("case config field 'candidate_signals' must be a list")
    if not all(isinstance(item, str) for item in payload["candidate_signals"]):
        raise ValueError("candidate_signals must contain only strings")


def _parse_month(value: str, label: str) -> Tuple[int, int]:
    parts = value.split("-")
    if len(parts) != 2 or len(parts[0]) != 4 or len(parts[1]) != 2:
        raise ValueError(f"{label} must use YYYY-MM format")
    try:
        year = int(parts[0])
        month = int(parts[1])
    except ValueError as exc:
        raise ValueError(f"{label} must use YYYY-MM format") from exc
    if not 1 <= month <= 12:
        raise ValueError(f"{label} month must be between 01 and 12")
    return year, month


def _month_index(value: str) -> int:
    year, month = _parse_month(value, value)
    return year * 12 + month


def _validate_monthly_sequence(dates: Tuple[str, ...]) -> None:
    previous = _month_index(dates[0])
    for index, date in enumerate(dates[1:], start=2):
        current = _month_index(date)
        if current <= previous:
            raise ValueError(f"CSV dates must be strictly increasing at row {index}")
        if current != previous + 1:
            raise ValueError(f"CSV dates must be monthly without gaps at row {index}")
        previous = current
