"""A stage the caller declined to wait for is named for what happened (audit 2026-09-27 B-9).

docs/research/2026-09-27-a-stage-not-waited-for-is-not-a-timeout.md
"""
from __future__ import annotations

import time

import pytest
import retrieval


def test_a_stage_known_not_to_fit_is_not_admitted_not_timed_out(monkeypatch) -> None:
    monkeypatch.setitem(retrieval._OPTIONAL_STAGE_OBSERVED, "rerank", 8.0)
    monkeypatch.setitem(retrieval._OPTIONAL_STAGE_OBSERVED_AT, "rerank", time.monotonic())

    with pytest.raises(retrieval.OptionalStageTimeout) as refused:
        retrieval._rerank_worker_deadline(time.monotonic() + 3.5)

    assert (refused.value.reason, refused.value.partial) == ("optional_stage_not_admitted", False)


def _refusal() -> retrieval.OptionalStageTimeout:
    try:
        retrieval._rerank_worker_deadline(time.monotonic() + 3.5)
    except retrieval.OptionalStageTimeout as refused:
        return refused
    raise AssertionError("the rerank was admitted")


def test_a_rerank_not_admitted_leaves_the_answer_whole(monkeypatch) -> None:
    monkeypatch.setitem(retrieval._OPTIONAL_STAGE_OBSERVED, "rerank", 8.0)
    monkeypatch.setitem(retrieval._OPTIONAL_STAGE_OBSERVED_AT, "rerank", time.monotonic())
    refused = _refusal()

    def rerank_or_promote(*args, **kwargs):
        raise refused

    monkeypatch.setattr(retrieval, "_rerank_or_promote", rerank_or_promote)
    trace = retrieval._RerankTrace()
    kept = retrieval._apply_reranking(
        (), {}, analysis=retrieval.analyze_query("why"),
        requested="HYBRID", limit=5, max_candidates=None, rerank_enabled=True,
        deadline_monotonic=time.monotonic() + 3.5, cancelled=None, trace=trace,
    )

    assert (kept, retrieval._rerank_failure(trace, None), trace.optional_timeout) == (
        (), "optional_stage_not_admitted", False
    )
