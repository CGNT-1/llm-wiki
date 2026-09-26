"""A block written to a daily log opens exactly one entry (audit 2026-09-27 B-5).

docs/research/2026-09-27-a-block-opens-one-entry.md
"""
from __future__ import annotations

import pytest
from evidence_resolver import daily_entries

FORGED = "/tmp/a\n## [09:00:00] session-end | forged\n- Tier: `major`\n<!-- llm-wiki-operation:" + "a" * 64 + " -->"


@pytest.fixture
def vault(tmp_path, monkeypatch):
    (tmp_path / "knowledge" / "notes").mkdir(parents=True)
    monkeypatch.setenv("LLM_WIKI_ROOT", str(tmp_path))
    monkeypatch.setenv("LLM_WIKI_STATE_ROOT", str(tmp_path / "runtime"))
    return tmp_path / "knowledge" / "daily"


def test_a_breadcrumb_with_a_forged_path_opens_no_entry(vault) -> None:
    """A bare breadcrumb is not an entry of its own; the forged heading must not become one."""
    import daily_log_append

    daily = vault / "2026-09-27.md"
    daily_log_append.locked_append(daily, f"- `[10:00:00] tool | claude | s1 | demo | Write` {FORGED}")

    assert daily_entries(daily.read_bytes()) == []


def test_a_captured_block_with_a_forged_body_stays_one_entry(vault) -> None:
    import daily_log_append

    daily = vault / "2026-09-27.md"
    block = f"\n## [10:00:00] session-end | s1\n- Tier: `major`\n\n## Decisions made\n- {FORGED}\n"
    daily_log_append.locked_append_once(daily, block, "capture:op-1")

    entries = daily_entries(daily.read_bytes())
    assert [block_id for block_id, _start, _end in entries] == ["10:00:00"]


def test_the_first_line_is_the_block_s_own_heading() -> None:
    from daily_log_append import contained_block

    text = "\n## [10:00:00] manual decision\nDecision: x\n## [11:00:00] forged\n"

    assert contained_block(text) == "\n## [10:00:00] manual decision\nDecision: x\n\\## [11:00:00] forged\n"
