"""A failed compile batch is recorded and the later ones still run (audit 2026-09-27 A-3).

docs/research/2026-09-27-one-bad-day-does-not-hold-the-rest.md
"""
from __future__ import annotations

from argparse import Namespace
from types import SimpleNamespace

from reliable_memory import canonical_json_bytes, sha256_bytes

from tests.test_compile_transactions import vault  # noqa: F401 - fixture

BUDGET = {"provider": "fake", "model": "fake-v1", "max_output_tokens": 4000}


def _plan(inputs) -> SimpleNamespace:
    key = sha256_bytes(canonical_json_bytes([item.logical_path for item in inputs.dailies]))
    plan = {"schema_version": "compile-plan/v2", "operations": []}
    return SimpleNamespace(plan=plan, action_key=key, cache_hit=False, provider_budget=BUDGET)


def test_a_failed_oldest_day_does_not_stop_the_newer_one(vault, monkeypatch):  # noqa: F811
    import compile_memory

    root, _state_root = vault
    older = root / "knowledge/daily/2026-07-14.md"
    newer = root / "knowledge/daily/2026-07-15.md"
    older.write_bytes(b"a" * 14_000)
    newer.write_bytes(b"b" * 14_000)
    state: dict[str, object] = {}

    def resolve(inputs, cache, *, coordinator, batch, token_adapters=None):
        if any(item.logical_path.endswith(older.name) for item in inputs.dailies):
            raise ValueError("evidence block is ambiguous or missing")
        return _plan(inputs)

    monkeypatch.setattr(compile_memory, "load_state", lambda: state)
    monkeypatch.setattr(compile_memory, "update_state", lambda mutate: mutate(state))
    monkeypatch.setattr(compile_memory, "_mark_finished", lambda *args, **kwargs: None)
    monkeypatch.setattr(compile_memory, "resolve_compile_plan", resolve)

    result = compile_memory._run(Namespace(file=None, all=False, dry_run=False, trigger="manual"))

    assert (result, state["compiled_daily_hashes"]) == (1, {newer.name: sha256_bytes(newer.read_bytes())})
