"""Source revision of the running web frontend.

This is a **source revision**, not a deployment identity. It answers "which
commit is this process running", and nothing more. Two services reporting the
same value were built from the same source; they were **not** necessarily
deployed together, and API and web are independent deployments.

Deliberately OUTSIDE the `pipeline_version` hash. `pipeline_version` identifies
the Report-producing implementation (versioning.py, adapter.py, nestor_delta/*);
this identifies the whole source tree, including routing, the ledger, and CORS,
none of which belong in a Report identity.

Resolution order - the platform's own value first, the manual override second,
so a stale hand-set variable can never shadow an authoritative one:

1. RAILWAY_GIT_COMMIT_SHA  (platform, present only for repo-linked deploys)
2. NESTOR_BUILD_SHA        (set by scripts/deploy-railway.sh at deploy time)
3. `git rev-parse`         (local checkouts; the deploy image excludes .git)
4. "unknown"

A candidate is accepted only if it is 7-40 hexadecimal characters after
stripping. Blank and malformed values are skipped, not passed through.

**"unknown" in a live deployment is a defect, not a benign default.** It means
the running process cannot say what it is. Fix the source; do not tolerate it.
"""

from __future__ import annotations

import os
import re
import subprocess

UNKNOWN = "unknown"
_SHA_PATTERN = re.compile(r"\A[0-9a-f]{7,40}\Z")
_ENV_VARS = ("RAILWAY_GIT_COMMIT_SHA", "NESTOR_BUILD_SHA")


def _valid(candidate: object) -> str:
    """Return the normalised revision, or "" if the candidate is unusable."""
    if not isinstance(candidate, str):
        return ""
    stripped = candidate.strip().lower()
    return stripped if _SHA_PATTERN.match(stripped) else ""


def _from_git() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short=12", "HEAD"],
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
    except Exception:  # noqa: BLE001 - identity is best-effort, never fatal
        return ""
    if result.returncode != 0:
        return ""
    return _valid(result.stdout)


def _detect() -> str:
    for var in _ENV_VARS:
        candidate = _valid(os.environ.get(var))
        if candidate:
            return candidate
    return _from_git() or UNKNOWN


SOURCE_REVISION = _detect()
