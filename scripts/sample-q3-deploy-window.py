#!/usr/bin/env python3
"""Capture canonical and cache-busted capabilities during an API deploy."""

from __future__ import annotations

import argparse
import json
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def fetch(url: str, mode: str, timeout: float) -> dict[str, Any]:
    started = time.perf_counter()
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "nestor-delta-q3-deploy-sampler/1",
            "X-Railway-Debug": "1",
        },
    )
    try:
        response = urllib.request.urlopen(request, timeout=timeout)
    except urllib.error.HTTPError as exc:
        response = exc
    except Exception as exc:
        return {
            "timestamp": utc_now(),
            "mode": mode,
            "url": url,
            "elapsed_ms": round((time.perf_counter() - started) * 1000),
            "error": f"{exc.__class__.__name__}: {exc}",
        }

    body_bytes = response.read()
    body_text = body_bytes.decode("utf-8", errors="replace")
    headers = {key.lower(): value for key, value in response.headers.items()}
    try:
        body: Any = json.loads(body_text)
    except json.JSONDecodeError:
        body = body_text
    payload = body if isinstance(body, dict) else {}
    return {
        "timestamp": utc_now(),
        "mode": mode,
        "url": url,
        "http_status": response.status,
        "elapsed_ms": round((time.perf_counter() - started) * 1000),
        "source_revision": payload.get("source_revision"),
        "pipeline_version": payload.get("pipeline_version"),
        "ledger_present": "ledger" in payload,
        "cache_control": headers.get("cache-control"),
        "age": headers.get("age"),
        "etag": headers.get("etag"),
        "x_railway_request_id": headers.get("x-railway-request-id"),
        "x_hikari_trace": headers.get("x-hikari-trace"),
        "x_railway_edge": headers.get("x-railway-edge"),
        "x_railway_upstream_zone": headers.get("x-railway-upstream-zone"),
        "headers": headers,
        "body": body,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Sample /api/v1/capabilities before, during, and after a Railway deploy. "
            "Start this before running scripts/deploy-railway.sh."
        )
    )
    parser.add_argument("base_url", help="API origin, for example https://api.example")
    parser.add_argument("output", type=Path, help="New directory for evidence.jsonl")
    parser.add_argument("--duration", type=float, default=180.0, help="Seconds to sample")
    parser.add_argument("--interval", type=float, default=1.0, help="Seconds between pairs")
    parser.add_argument("--timeout", type=float, default=20.0, help="Per-request timeout")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.duration <= 0 or args.interval <= 0 or args.timeout <= 0:
        raise SystemExit("duration, interval, and timeout must be positive")

    args.output.mkdir(parents=True, exist_ok=False)
    evidence_path = args.output / "evidence.jsonl"
    endpoint = f"{args.base_url.rstrip('/')}/api/v1/capabilities"
    deadline = time.monotonic() + args.duration
    next_cycle = time.monotonic()
    recorded = 0
    successful = 0

    print(f"Writing Q3 deployment evidence to {evidence_path}", flush=True)
    with evidence_path.open("w", encoding="utf-8") as handle:
        while time.monotonic() < deadline:
            urls = (
                ("canonical", endpoint),
                ("cache_busted", f"{endpoint}?cb=q3-{uuid4().hex}"),
            )
            for mode, url in urls:
                record = fetch(url, mode, args.timeout)
                handle.write(json.dumps(record, sort_keys=True) + "\n")
                handle.flush()
                recorded += 1
                if record.get("http_status") == 200:
                    successful += 1
                print(
                    f"{record['timestamp']} {mode:12} "
                    f"status={record.get('http_status', 'ERR')} "
                    f"revision={record.get('source_revision')} "
                    f"cache_control={record.get('cache_control')}",
                    flush=True,
                )
            next_cycle += args.interval
            time.sleep(max(0.0, next_cycle - time.monotonic()))

    print(f"Recorded {recorded} requests ({successful} HTTP 200).", flush=True)
    return 0 if successful else 1


if __name__ == "__main__":
    raise SystemExit(main())
