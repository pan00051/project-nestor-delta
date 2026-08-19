"""FastAPI wrapper for the thin Delta website adapter."""

from __future__ import annotations

from typing import Any

from .adapter import analyze_payload, audit_payload, snapshot_payload
from .errors import SCHEMA_VERSION

try:  # FastAPI is a deployment dependency, not needed for adapter unit tests.
    from fastapi import FastAPI
    from fastapi.responses import JSONResponse
except ModuleNotFoundError:  # pragma: no cover - exercised only without FastAPI.
    FastAPI = None  # type: ignore[assignment]
    JSONResponse = None  # type: ignore[assignment]


def create_app():
    if FastAPI is None:
        raise RuntimeError("FastAPI is not installed. Install deployment dependencies first.")

    app = FastAPI(title="Nestor Delta API", version="0.1.0")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "schema_version": SCHEMA_VERSION}

    @app.get("/schema/report")
    def report_schema() -> dict[str, str]:
        return {"schema_version": SCHEMA_VERSION}

    @app.post("/analyze")
    def analyze(payload: dict[str, Any]):
        status, report = analyze_payload(payload)
        return JSONResponse(status_code=status, content=report)

    @app.post("/audit")
    def audit(payload: dict[str, Any]):
        status, report = audit_payload(payload)
        return JSONResponse(status_code=status, content=report)

    @app.post("/snapshot")
    def snapshot(payload: dict[str, Any]):
        status, report = snapshot_payload(payload)
        return JSONResponse(status_code=status, content=report)

    return app


app = create_app() if FastAPI is not None else None
