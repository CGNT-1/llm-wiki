"""A context answer fits the budget it was given, names each item once, and counts one way (audit 2026-09-27 B-12).

One page returned 200 bytes of text inside 4.3 KB of lists and traces; the budget
bounded only the text, counted at one token per byte, while the cost block counted
`chars/4`. See docs/research/2026-09-27-a-context-answer-fits-the-budget-it-was-given.md.
"""
from __future__ import annotations

import json
from pathlib import Path

import answer_budget
import answer_cost
import code_navigation_renderer
import mcp_server
import memory_state
import pytest

SLUGS = ["choice", "incident", "state"]
ANSWER_KEYS = {
    "text", "packed_tokens", "token_budget", "corpus_generation", "repo_map", "items", "dropped",
    "missing_slugs", "include", "collected_at",
}


@pytest.fixture
def vault(tmp_path: Path, monkeypatch) -> Path:
    notes, project = tmp_path / "knowledge/notes", tmp_path / "knowledge/projects/demo"
    notes.mkdir(parents=True)
    project.mkdir(parents=True)
    (notes / "choice.md").write_text(
        "---\ntype: decision\nstatus: active\n---\n# Choice\n\nOne-sentence summary: Keep one package.\n\n"
        "## Evidence\n\nproof\n", encoding="utf-8")
    (notes / "incident.md").write_text(
        "---\ntype: debugging\nstatus: active\n---\n# Incident\n\nOne-sentence summary: Compiler regression.\n",
        encoding="utf-8")
    (project / "state.md").write_text(
        "---\ntype: project-state\nstatus: active\n---\n# Demo\n\nOne-sentence summary: Active Task17.\n",
        encoding="utf-8")
    monkeypatch.setattr(memory_state, "ROOT", tmp_path)
    return tmp_path


# The same bytes these budgets held under the earlier 4-bytes estimate (400 and 1200).
@pytest.mark.parametrize("budget", [800, 2400])
def test_the_whole_answer_fits_the_budget_not_only_its_text(vault: Path, budget: int) -> None:
    answer = mcp_server._get_context(SLUGS, token_budget=budget)

    assert answer_budget.estimate_tokens(answer) <= budget


def test_the_answer_names_each_item_once(vault: Path) -> None:
    answer = mcp_server._get_context(SLUGS, token_budget=1200)
    places = [json.dumps(item, sort_keys=True) for item in answer["items"]]

    assert (set(answer), len(places)) == (ANSWER_KEYS, len(set(places)))


def test_an_item_does_not_spell_its_source_again(vault: Path) -> None:
    answer = mcp_server._get_context(SLUGS, token_budget=1200)

    assert [item for item in answer["items"] if {"item_id", "source_sha256", "text"} & set(item)] == []


def test_every_answer_counts_tokens_one_way(vault: Path) -> None:
    answer = mcp_server._get_context(SLUGS, token_budget=1200)

    assert (
        answer["packed_tokens"] == answer_budget.estimate_text_tokens(answer["text"]),
        code_navigation_renderer.estimate_tokens is answer_budget.estimate_text_tokens,
        answer_cost.ESTIMATE_METHOD,
    ) == (True, True, "utf8_bytes/2")


def test_the_estimate_counts_bytes_so_cyrillic_is_not_undercounted() -> None:
    assert (answer_budget.estimate_text_tokens("abcd"), answer_budget.estimate_text_tokens("привет")) == (2, 6)


def test_a_budget_the_item_list_cannot_fit_is_refused_not_exceeded(vault: Path, monkeypatch) -> None:
    monkeypatch.setattr(answer_budget, "estimate_tokens", lambda data: 10**6)

    with pytest.raises(ValueError, match="token_budget cannot hold"):
        mcp_server._get_context(SLUGS, token_budget=400)
