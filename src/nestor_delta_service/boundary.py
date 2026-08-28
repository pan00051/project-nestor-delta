"""API v1 resource boundary helpers."""

from __future__ import annotations

import json
import logging
import os
from collections import OrderedDict
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock
from time import perf_counter
from typing import Any, Mapping
from uuid import uuid4

from nestor_delta_web import presets

from .adapter import SUPPORTED_CASES
from .build_info import SOURCE_REVISION
from .errors import SCHEMA_VERSION, not_found
from .versioning import PIPELINE_VERSION

API_VERSION = "v1"
RUN_STORE_MAX = 100
MAX_UPLOAD_BYTES = 5 * 1024 * 1024
REPO_ROOT = Path(__file__).resolve().parents[2]
LOGGER = logging.getLogger(__name__)


class RunStore:
    """Bounded process-lifetime store for API v1 run envelopes."""

    def __init__(self, max_runs: int = RUN_STORE_MAX):
        self.max_runs = max_runs
        self._items: OrderedDict[str, dict[str, Any]] = OrderedDict()
        self._lock = RLock()

    def put(self, envelope: dict[str, Any]) -> None:
        run_id = str(envelope["run"]["run_id"])
        with self._lock:
            self._items[run_id] = envelope
            self._items.move_to_end(run_id)
            while len(self._items) > self.max_runs:
                self._items.popitem(last=False)

    def get(self, run_id: str) -> dict[str, Any] | None:
        with self._lock:
            return self._items.get(run_id)

    def clear(self) -> None:
        with self._lock:
            self._items.clear()


RUN_STORE = RunStore()
LEDGER_LOCK = RLock()
DEFAULT_RELATIONSHIP_LEDGER_PATH = Path("/tmp/nestor_delta_relationship_ledger.jsonl")
_LEDGER_LAST_WRITE_OK: bool | None = None


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def relationship_ledger_path() -> Path:
    return Path(
        os.environ.get(
            "NESTOR_RELATIONSHIP_LEDGER_PATH",
            str(DEFAULT_RELATIONSHIP_LEDGER_PATH),
        )
    )


def reset_relationship_ledger_observation() -> None:
    global _LEDGER_LAST_WRITE_OK
    _LEDGER_LAST_WRITE_OK = None


def _ledger_line_count(path: Path) -> int | None:
    if not path.exists():
        return 0
    if not path.is_file():
        return None
    with path.open("r", encoding="utf-8") as handle:
        return sum(1 for _ in handle)


def _probe_relationship_ledger(path: Path) -> tuple[bool, str | None]:
    probe_path = path.parent / f".{path.name}.probe-{uuid4().hex}"
    payload = "nestor-delta-ledger-probe\n"
    try:
        if path.exists() and not path.is_file():
            return False, "ledger path is not a file"
        path.parent.mkdir(parents=True, exist_ok=True)
        with probe_path.open("w", encoding="utf-8") as handle:
            handle.write(payload)
        if probe_path.read_text(encoding="utf-8") != payload:
            return False, "ledger write probe readback mismatch"
        return True, None
    except Exception as exc:
        return False, f"{exc.__class__.__name__}: {exc}"
    finally:
        try:
            probe_path.unlink()
        except FileNotFoundError:
            pass
        except Exception:
            LOGGER.exception("relationship ledger probe cleanup failed")


def relationship_ledger_status() -> dict[str, Any]:
    configured_path = os.environ.get("NESTOR_RELATIONSHIP_LEDGER_PATH")
    path = relationship_ledger_path()
    with LEDGER_LOCK:
        writable, probe_error = _probe_relationship_ledger(path)
        try:
            lines = _ledger_line_count(path) if writable else None
        except Exception as exc:
            writable = False
            lines = None
            probe_error = f"{exc.__class__.__name__}: {exc}"
    return {
        "enabled": True,
        "configured": bool(configured_path),
        "durable": bool(configured_path) and writable,
        "writable": writable,
        "last_write_ok": _LEDGER_LAST_WRITE_OK,
        "lines": lines,
        "path": str(path),
        "write_probe_error": probe_error,
    }


def capabilities() -> dict[str, Any]:
    return {
        "api_version": API_VERSION,
        "report_schema_version": SCHEMA_VERSION,
        "pipeline_version": PIPELINE_VERSION,
        "source_revision": SOURCE_REVISION,
        "inputs": {
            "bundled_cases": sorted(SUPPORTED_CASES),
            "csv_upload": True,
            "max_upload_bytes": MAX_UPLOAD_BYTES,
        },
        "eurostat": {
            "enabled": True,
            "presets": presets.capability_presets(),
            "dataset_search": False,
        },
        "execution": {"mode": "sync"},
        "run_retention": {
            "mode": "in_memory_process_lifetime",
            "max_runs": RUN_STORE.max_runs,
        },
        "ledger": relationship_ledger_status(),
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


def append_relationship_ledger(envelope: Mapping[str, Any]) -> None:
    """Append selected-relation outcome candidates outside the Report body."""
    global _LEDGER_LAST_WRITE_OK
    try:
        report = envelope.get("report")
        run = envelope.get("run") or {}
        if not isinstance(report, Mapping):
            return
        selected = [
            relation
            for relation in report.get("relations", []) or []
            if isinstance(relation, Mapping) and relation.get("selected") is True
        ]
        if not selected:
            return

        path = relationship_ledger_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        snapshot = report.get("snapshot") or {}
        case = report.get("case") or {}
        with LEDGER_LOCK:
            with path.open("a", encoding="utf-8") as handle:
                for relation in selected:
                    effect = relation.get("effect") or {}
                    entry = {
                        "mode": "realtime",
                        "run_id": run.get("run_id"),
                        "snapshot_hash": snapshot.get("hash"),
                        "target": relation.get("target") or case.get("target"),
                        "source": relation.get("source"),
                        "lag": relation.get("lag"),
                        "sign": effect.get("sign"),
                        "score": effect.get("score"),
                        "stability": relation.get("stability"),
                        "generated_as_of": report.get("generated_as_of"),
                        "pipeline_version": report.get("pipeline_version"),
                    }
                    handle.write(json.dumps(entry, sort_keys=True) + "\n")
            _LEDGER_LAST_WRITE_OK = True
    except Exception:
        _LEDGER_LAST_WRITE_OK = False
        LOGGER.exception(
            "relationship ledger append failed; analysis response will continue"
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
