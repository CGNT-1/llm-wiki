"""A self-update puts back what it set aside on any failure and costs what it says (audit 2026-09-27 C-13).

docs/research/2026-09-27-an-update-costs-what-it-says.md
"""
from __future__ import annotations

import subprocess

import self_update

from tests.test_an_untracked_copy_of_the_update_does_not_stop_it import (  # noqa: F401
    NOTE,
    note_upstream,
)
from tests.test_self_update import linked_clone  # noqa: F401


def test_a_merge_that_times_out_puts_the_copy_back(note_upstream, monkeypatch) -> None:  # noqa: F811
    (note_upstream / NOTE).write_text("# A note\n", encoding="utf-8")
    real_git = self_update._git

    def slow_merge(root, *arguments, **kwargs):
        if arguments[0] == "merge":
            raise subprocess.TimeoutExpired(["git", "merge"], self_update.GIT_TIMEOUT_SECONDS)
        return real_git(root, *arguments, **kwargs)

    monkeypatch.setattr(self_update, "_git", slow_merge)

    outcome = self_update.update_checkout(note_upstream)

    assert (outcome["status"], (note_upstream / NOTE).read_text(encoding="utf-8")) == ("error", "# A note\n")


def _git_calls(commands: list[tuple[str, ...]]) -> tuple[int, int]:
    """(fetches, other git calls) among the commands an update ran."""
    git = [command[1] for command in commands if command[0] == "git"]
    return git.count("fetch"), len(git) - git.count("fetch")


def test_a_full_update_makes_no_more_calls_than_its_bound_counts(note_upstream, monkeypatch) -> None:  # noqa: F811
    (note_upstream / NOTE).write_text("# A note\n", encoding="utf-8")
    commands: list[tuple[str, ...]] = []
    real_run = self_update._run

    def counted(command, **kwargs):
        commands.append(tuple(command))
        return real_run(command, **kwargs)

    monkeypatch.setattr(self_update, "_run", counted)

    outcome = self_update.update_checkout(note_upstream)

    assert (outcome["status"], *_git_calls(commands)) == (
        "updated", self_update.FETCHES_PER_UPDATE, self_update.GIT_CALLS_PER_UPDATE
    )
