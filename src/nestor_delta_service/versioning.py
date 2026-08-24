"""Version identifiers for Delta analysis reports."""

from __future__ import annotations

import hashlib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def pipeline_version() -> str:
    digest = hashlib.sha256()
    paths = (
        Path(__file__),
        Path(__file__).with_name("adapter.py"),
        *sorted((REPO_ROOT / "src" / "nestor_delta").glob("*.py")),
    )
    for path in paths:
        digest.update(path.relative_to(REPO_ROOT).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return f"s10.sha256.{digest.hexdigest()[:12]}"


PIPELINE_VERSION = pipeline_version()
