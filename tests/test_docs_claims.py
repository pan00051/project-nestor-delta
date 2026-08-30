"""Mechanical check that Markdown path claims point at real files."""

from __future__ import annotations

import re
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
PATH_RE = re.compile(
    r"`("
    r"(?:scripts|src|tests|docs)/[A-Za-z0-9_./*-]+\.(?:py|md|json|sh|jsonl)"
    r")`"
)
EXEMPTION_MARKERS = ("(historical)", "(quarantined)")
EXEMPTION_WINDOW = 40
QUARANTINED_ARTIFACTS = {
    "docs/evidence/G0_DRAFT_QUARANTINE_2026-08-30/ALGORITHM_EXPERIMENTS.md",
    "docs/evidence/G0_DRAFT_QUARANTINE_2026-08-30/algorithm_seed_sets_v1.json",
    "docs/evidence/G0_DRAFT_QUARANTINE_2026-08-30/run_algorithm_experiment.py",
    "docs/evidence/G0_DRAFT_QUARANTINE_2026-08-30/test_algorithm_experiment_log.py",
}


def test_markdown_path_references_exist_or_are_explicitly_planned() -> None:
    missing: list[str] = []
    for path in _markdown_files():
        if _is_quarantined_artifact(path):
            continue
        for paragraph in _paragraphs(path.read_text(encoding="utf-8")):
            if "Planned — not yet implemented" in paragraph:
                continue
            for match in PATH_RE.finditer(paragraph):
                claimed = match.group(1).rstrip(".,);:]")
                if "*" in claimed:
                    continue
                if _has_reference_exemption(paragraph, match):
                    continue
                if not (REPO / claimed).exists():
                    missing.append(f"{path.relative_to(REPO)}: {claimed}")

    assert not missing, "Missing Markdown path references:\n" + "\n".join(sorted(missing))


def _markdown_files() -> list[Path]:
    roots = [REPO, REPO / "docs"]
    files: set[Path] = set()
    for root in roots:
        files.update(root.rglob("*.md"))
    return sorted(path for path in files if ".pytest_cache" not in path.parts)


def _paragraphs(text: str) -> list[str]:
    return re.split(r"\n\s*\n", text)


def _has_reference_exemption(paragraph: str, match: re.Match[str]) -> bool:
    scope_end = min(len(paragraph), match.end() + EXEMPTION_WINDOW)
    line_end = paragraph.find("\n", match.end(), scope_end)
    if line_end != -1:
        scope_end = line_end
    next_reference = PATH_RE.search(paragraph, match.end(), scope_end)
    if next_reference is not None:
        scope_end = next_reference.start()
    suffix = paragraph[match.end():scope_end]
    return any(marker in suffix for marker in EXEMPTION_MARKERS)


def _is_quarantined_artifact(path: Path) -> bool:
    relative = path.relative_to(REPO).as_posix()
    return relative in QUARANTINED_ARTIFACTS
