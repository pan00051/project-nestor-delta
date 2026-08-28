"""FastAPI wrapper for the thin Delta website adapter."""

from __future__ import annotations

import logging
from time import perf_counter
from typing import Any, Optional

from .adapter import analyze_payload, audit_payload, snapshot_payload
from .boundary import (
    RUN_STORE,
    append_relationship_ledger,
    capabilities as capabilities_payload,
    completed_envelope,
    failed_envelope,
    relationship_ledger_status,
    run_not_found,
    utc_now,
)
from .build_info import SOURCE_REVISION
from .errors import SCHEMA_VERSION

LOGGER = logging.getLogger(__name__)

try:  # FastAPI is a deployment dependency, not needed for adapter unit tests.
    from fastapi import Depends, FastAPI, Header
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import JSONResponse
except ModuleNotFoundError:  # pragma: no cover - exercised only without FastAPI.
    FastAPI = None  # type: ignore[assignment]
    Depends = None  # type: ignore[assignment]
    Header = None  # type: ignore[assignment]
    CORSMiddleware = None  # type: ignore[assignment]
    JSONResponse = None  # type: ignore[assignment]

_AUTH_HEADER = Header(default=None) if Header is not None else None
_PROVENANCE_HEADERS = {"Cache-Control": "no-store"}

def allow_request(
    authorization: Optional[str] = _AUTH_HEADER,  # type: ignore[assignment]
) -> None:
    """Single auth dependency stub. Local/dev v1 allows all requests."""
    _ = authorization


def submit_run(payload: dict[str, Any], client: Optional[str] = None) -> tuple[int, dict[str, Any]]:
    created_at = utc_now()
    started_at = perf_counter()
    status, report = analyze_payload(payload)
    if status == 200:
        envelope = completed_envelope(
            report,
            client=client,
            created_at=created_at,
            started_at=started_at,
        )
        RUN_STORE.put(envelope)
        append_relationship_ledger(envelope)
        return status, envelope
    if status == 500:
        envelope = failed_envelope(
            report,
            client=client,
            created_at=created_at,
            started_at=started_at,
        )
        RUN_STORE.put(envelope)
        return status, envelope
    return status, report


def create_app():
    if FastAPI is None:
        raise RuntimeError("FastAPI is not installed. Install deployment dependencies first.")

    app = FastAPI(title="Nestor Delta API", version="0.1.0")
    ledger = relationship_ledger_status()
    LOGGER.info(
        "relationship ledger path=%s durable=%s writable=%s lines=%s",
        ledger["path"],
        ledger["durable"],
        ledger["writable"],
        ledger["lines"],
    )
    logging.getLogger("uvicorn.error").info(
        "relationship ledger path=%s durable=%s writable=%s lines=%s",
        ledger["path"],
        ledger["durable"],
        ledger["writable"],
        ledger["lines"],
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    def health():
        return JSONResponse(
            content={
                "status": "ok",
                "schema_version": SCHEMA_VERSION,
                "source_revision": SOURCE_REVISION,
                "ledger": relationship_ledger_status(),
            },
            headers=_PROVENANCE_HEADERS,
        )

    @app.get("/schema/report")
    def report_schema() -> dict[str, str]:
        return {"schema_version": SCHEMA_VERSION}

    @app.post("/api/v1/runs", dependencies=[Depends(allow_request)])
    def create_run(
        payload: dict[str, Any],
        x_nestor_client: Optional[str] = Header(default=None),
    ):
        status, body = submit_run(payload, client=x_nestor_client)
        return JSONResponse(status_code=status, content=body)

    @app.get("/api/v1/runs/{run_id}", dependencies=[Depends(allow_request)])
    def get_run(run_id: str):
        envelope = RUN_STORE.get(run_id)
        if envelope is None:
            status, report = run_not_found(run_id)
            return JSONResponse(status_code=status, content=report)
        return JSONResponse(status_code=200, content=envelope)

    @app.get("/api/v1/capabilities", dependencies=[Depends(allow_request)])
    def capabilities():
        return JSONResponse(content=capabilities_payload(), headers=_PROVENANCE_HEADERS)

    @app.post("/analyze", dependencies=[Depends(allow_request)])
    def analyze(payload: dict[str, Any]):
        status, report = analyze_payload(payload)
        return JSONResponse(status_code=status, content=report)

    @app.post("/api/v1/audit", dependencies=[Depends(allow_request)])
    @app.post("/audit", dependencies=[Depends(allow_request)])
    def audit(payload: dict[str, Any]):
        status, report = audit_payload(payload)
        return JSONResponse(status_code=status, content=report)

    @app.post("/api/v1/snapshot", dependencies=[Depends(allow_request)])
    @app.post("/snapshot", dependencies=[Depends(allow_request)])
    def snapshot(payload: dict[str, Any]):
        status, report = snapshot_payload(payload)
        return JSONResponse(status_code=status, content=report)

    return app


app = create_app() if FastAPI is not None else None
