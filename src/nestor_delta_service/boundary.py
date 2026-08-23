"""API v1 resource boundary helpers."""

from __future__ import annotations

from collections import OrderedDict
from datetime import datetime, timezone
from time import perf_counter
from typing import Any, Mapping
from uuid import uuid4

from nestor_delta_web import presets

from .adapter import SUPPORTED_CASES
from .errors import SCHEMA_VERSION, not_found

API_VERSION = "v1"
PIPELINE_VERSION = "s10.2026.08.1"
RUN_STORE_MAX = 100
MAX_UPLOAD_BYTES = 5 * 1024 * 1024


class RunStore:
    """Bounded process-lifetime store for API v1 run envelopes."""

    def __init__(self, max_runs: int = RUN_STORE_MAX):
        self.max_runs = max_runs
        self._items: OrderedDict[str, dict[str, Any]] = OrderedDict()

    def put(self, envelope: dict[str, Any]) -> None:
        run_id = str(envelope["run"]["run_id"])
        self._items[run_id] = envelope
        self._items.move_to_end(run_id)
        while len(self._items) > self.max_runs:
            self._items.popitem(last=False)

    def get(self, run_id: str) -> dict[str, Any] | None:
        return self._items.get(run_id)

    def clear(self) -> None:
        self._items.clear()


RUN_STORE = RunStore()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def capabilities() -> dict[str, Any]:
    return {
        "api_version": API_VERSION,
        "report_schema_version": SCHEMA_VERSION,
        "pipeline_version": PIPELINE_VERSION,
        "inputs": {
            "bundled_cases": sorted(SUPPORTED_CASES),
            "csv_upload": True,
            "max_upload_bytes": MAX_UPLOAD_BYTES,
        },
        "eurostat": {
            "enabled": True,
            "presets": sorted(presets.EUROSTAT_PRESETS),
            "dataset_search": False,
        },
        "execution": {"mode": "sync"},
        "run_retention": {
            "mode": "in_memory_process_lifetime",
            "max_runs": RUN_STORE.max_runs,
        },
        "features": {
            "pdf_export": False,
            "report_persistence": False,
            "sharing": False,
        },
    }


def make_run_envelope(
    report: dict[str, Any] | None,
    *,
    status: str,
    client: str | None,
    created_at: str,
    completed_at: str | None,
    duration_ms: int,
    run_id: str | None = None,
    report_id: str | None = None,
) -> dict[str, Any]:
    return {
        "run": {
            "run_id": run_id or str(uuid4()),
            "report_id": report_id if status == "completed" else None,
            "status": status,
            "api_version": API_VERSION,
            "created_at": created_at,
            "completed_at": completed_at,
            "duration_ms": duration_ms,
            "client": client,
            "requested_by": None,
            "tenant_id": None,
        },
        "report": report if status == "completed" else None,
    }


def completed_envelope(
    report: dict[str, Any],
    *,
    client: str | None,
    created_at: str,
    started_at: float,
) -> dict[str, Any]:
    return make_run_envelope(
        report,
        status="completed",
        client=client,
        created_at=created_at,
        completed_at=utc_now(),
        duration_ms=int((perf_counter() - started_at) * 1000),
        report_id=str(uuid4()),
    )


def failed_envelope(
    report: dict[str, Any],
    *,
    client: str | None,
    created_at: str,
    started_at: float,
) -> dict[str, Any]:
    envelope = make_run_envelope(
        report,
        status="failed",
        client=client,
        created_at=created_at,
        completed_at=utc_now(),
        duration_ms=int((perf_counter() - started_at) * 1000),
    )
    envelope.update(report)
    return envelope


def run_not_found(run_id: str) -> tuple[int, dict[str, Any]]:
    error = not_found(
        "run_not_found",
        f"Run {run_id!r} was not found.",
        field="run_id",
        detail={"run_id": run_id},
    )
    return error.http_status, error.to_report()
