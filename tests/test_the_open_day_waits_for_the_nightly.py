"""The session start compiles closed days only; the day still being appended to waits.

A day under 16 KB is one compile part, so every append changed its digest and every
session start sent the whole day again, padded to the compile window: on 2026-09-11,
36 KB of day text in six batches for a 10.6 KB day (compile receipts). See
docs/research/2026-09-27-an-estimate-is-measured-and-an-open-day-waits.md.
"""
from __future__ import annotations

import sys
from argparse import Namespace
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

CLOSED, OPEN = "2026-09-26.md", "2026-09-27.md"


@pytest.fixture
def vault(tmp_path, monkeypatch):
    """Two days, neither compiled: yesterday's is closed, today's is still growing."""
    root, state_root = tmp_path / "vault", tmp_path / "state"
    daily = root / "knowledge" / "daily"
    daily.mkdir(parents=True)
    (state_root / "run").mkdir(parents=True)
    for name in (CLOSED, OPEN):
        (daily / name).write_text("## [10:00:00] s\n", encoding="utf-8")
    (daily / "README.md").write_text("# Daily logs\n", encoding="utf-8")
    monkeypatch.setenv("LLM_WIKI_ROOT", str(root))
    monkeypatch.setenv("LLM_WIKI_STATE_ROOT", str(state_root))
    for name in ("maybe_compile", "memory_state", "compile_memory"):
        monkeypatch.delitem(sys.modules, name, raising=False)
    return root


def test_closed_days_are_every_day_but_the_newest(vault):
    import memory_state

    assert [path.name for path in memory_state.closed_daily_logs(vault / "knowledge/daily")] == [CLOSED]


def test_only_the_open_day_changed_is_no_work_for_the_session_start(vault):
    import maybe_compile
    from memory_state import file_hash, update_state

    daily = vault / "knowledge/daily"
    update_state(lambda state: state.update(compiled_daily_hashes={CLOSED: file_hash(daily / CLOSED)}))

    assert (maybe_compile._has_pending_work(closed_days_only=True), maybe_compile._has_pending_work()) == (False, True)


def test_the_session_start_compile_leaves_out_the_open_day(vault):
    import compile_memory

    offered = compile_memory._offered_dailies(Namespace(file=None, closed_days_only=True))
    everything = compile_memory._offered_dailies(Namespace(file=None))

    assert ([path.name for path in offered], [path.name for path in everything]) == ([CLOSED], [CLOSED, OPEN])


def test_the_spawned_compile_is_told_to_leave_the_open_day(vault):
    import maybe_compile

    assert (
        maybe_compile._compile_command("token", True)[-1],
        "--closed-days-only" in maybe_compile._compile_command("token", False),
    ) == ("--closed-days-only", False)


def test_the_session_start_asks_for_closed_days_only(monkeypatch):
    import integration_adapter
    import session_start_context

    asked: list[dict] = []
    monkeypatch.setattr(integration_adapter, "_run_maintenance_command", lambda *_args: None)
    monkeypatch.setattr(session_start_context, "maybe_spawn_nightly_catchup", lambda: None)
    monkeypatch.setattr(integration_adapter, "spawn_compile_if_idle", lambda **kwargs: asked.append(kwargs))

    integration_adapter._run_session_start_maintenance()

    assert asked == [{"closed_days_only": True}]


def test_an_answer_estimate_never_undercounts_measured_markdown():
    """2.30 bytes/token is the lowest ratio measured on this vault's raw Markdown (2026-09-27)."""
    import answer_budget

    assert answer_budget.BYTES_PER_TOKEN <= 2.30
