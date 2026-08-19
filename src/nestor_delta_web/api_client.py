"""Server-side HTTP client for the Delta API.

All requests originate from the Streamlit server process (never the browser), so
there is no CORS surface. The base URL is configured with DELTA_API_BASE_URL and
defaults to http://localhost:8000 — no production address is hard-coded.

This module never imports `nestor_delta`. It only speaks HTTP.
"""

from __future__ import annotations

import os
from typing import Any, Mapping, Optional

import requests

DEFAULT_BASE_URL = "http://localhost:8000"
DEFAULT_TIMEOUT = 30.0


def base_url() -> str:
    return os.environ.get("DELTA_API_BASE_URL", DEFAULT_BASE_URL).rstrip("/")


class ApiResult:
    """Uniform result: an HTTP (status, body) OR a transport failure."""

    def __init__(self, status: Optional[int], body: Optional[Mapping[str, Any]],
                 transport: Optional[str] = None, raw: Optional[str] = None):
        self.status = status
        self.body = body
        self.transport = transport   # "unreachable" | "timeout" | "malformed" | None
        self.raw = raw


def _post(path: str, payload: Mapping[str, Any], timeout: float) -> ApiResult:
    url = f"{base_url()}{path}"
    try:
        resp = requests.post(url, json=payload, timeout=timeout)
    except requests.exceptions.Timeout:
        return ApiResult(None, None, transport="timeout")
    except requests.exceptions.ConnectionError:
        return ApiResult(None, None, transport="unreachable")
    except requests.exceptions.RequestException:
        return ApiResult(None, None, transport="unreachable")
    try:
        body = resp.json()
    except ValueError:
        return ApiResult(resp.status_code, None, transport="malformed",
                         raw=resp.text[:2000])
    if not isinstance(body, dict):
        return ApiResult(resp.status_code, None, transport="malformed",
                         raw=str(body)[:2000])
    return ApiResult(resp.status_code, body)


def health(timeout: float = 5.0) -> ApiResult:
    url = f"{base_url()}/health"
    try:
        resp = requests.get(url, timeout=timeout)
        return ApiResult(resp.status_code, resp.json())
    except requests.exceptions.Timeout:
        return ApiResult(None, None, transport="timeout")
    except (requests.exceptions.ConnectionError, requests.exceptions.RequestException):
        return ApiResult(None, None, transport="unreachable")
    except ValueError:
        return ApiResult(None, None, transport="malformed")


def snapshot(payload: Mapping[str, Any], timeout: float = DEFAULT_TIMEOUT) -> ApiResult:
    return _post("/snapshot", payload, timeout)


def audit(payload: Mapping[str, Any], timeout: float = DEFAULT_TIMEOUT) -> ApiResult:
    return _post("/audit", payload, timeout)


def analyze(payload: Mapping[str, Any], timeout: float = DEFAULT_TIMEOUT) -> ApiResult:
    return _post("/analyze", payload, timeout)
