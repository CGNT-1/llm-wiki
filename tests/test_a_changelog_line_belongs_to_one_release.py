"""A changelog entry sits in one release section, never copied into shipped ones (audit 2026-09-27 B-18).

docs/research/2026-09-27-a-changelog-line-belongs-to-one-release.md
"""
from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path

CHANGELOG = Path(__file__).resolve().parents[1] / "CHANGELOG.md"


def _entries() -> list[tuple[str, str]]:
    """(entry line, section heading) for every bullet in the file."""
    parts = re.split(r"(?m)^## ", CHANGELOG.read_text(encoding="utf-8"))[1:]
    pairs = [(line, part.split("\n", 1)[0]) for part in parts for line in part.splitlines()]
    return [(line, section) for line, section in pairs if line.startswith("- ")]


def test_no_entry_appears_in_two_release_sections() -> None:
    homes: dict[str, list[str]] = defaultdict(list)
    for line, section in _entries():
        homes[line].append(section)

    assert {line[:80]: names for line, names in homes.items() if len(names) > 1} == {}
