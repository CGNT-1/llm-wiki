# Every child a script waits for has a deadline

Date: 2026-09-27. Audit 2026-09-27, finding C-9 (the rest of C-13 of 2026-09-26).

## What was wrong

The guard "every git call has a deadline" recognised only a call whose argv is a literal
list starting with `"git"`. `cleanup_worktrees._run` builds its argv with `_argv(cmd)`,
so two untimed git waits passed. Widening the question to its class — any
`subprocess.run/check_output/check_call/call` without `timeout` in `scripts/` — found
five: the two in `cleanup_worktrees`, `export_vault._run` (git archive, rev-parse, diff),
the queue's manual compile child, and the index rebuild child in `query_memory`.

## Decision

- `repository_scope.LOCAL_GIT_TIMEOUT_SECONDS = 60.0` for one local git call: measured
  here, `git archive` of the whole repository (the slowest local call) took 0.93 s for
  7.6 MB; 60 s is the bound the nightly update already gives one git call.
  `cleanup_worktrees` now imports it and `GIT_NO_CONFIG_COMMANDS` (its own copy is gone)
  and turns a timeout into the `RuntimeError` its callers already handle.
- The queue's manual compile waits `scheduled_nightly.compile_wait_seconds()` — the
  measured, operator-settable bound for one compile (now public; its only other caller
  is the nightly).
- The index rebuild child waits `INDEX_REBUILD_SECONDS = 60.0`: measured 0.11–0.24 s for
  209 pages with the interpreter, and the builder refuses more than `MAX_PAGE_COUNT`.
- Guard: `tests/test_every_git_call_has_a_deadline.py` now refuses any waited child
  without a timeout; it fails on the previous scripts.

Alternatives considered: a list of known wrappers (rejected — a new wrapper would hide
again); one universal timeout (rejected — a compile and a `git rev-parse` differ by
four orders of magnitude, so each bound carries its own measured basis).

## Sources (fetched 2026-09-27)

- Google SRE Book, Addressing Cascading Failures,
  https://sre.google/sre-book/addressing-cascading-failures/ — "It's usually wise to set a
  deadline. Setting either no deadline or an extremely high deadline may cause short-term
  problems that have long since passed to continue to consume server resources until the
  server restarts."
- Python documentation, subprocess.run, https://docs.python.org/3/library/subprocess.html —
  "If the timeout expires, the child process will be killed and waited for. The
  TimeoutExpired exception will be re-raised after the child process has terminated."
- Git documentation, git(1), https://git-scm.com/docs/git#_environment_variables —
  `GIT_OPTIONAL_LOCKS`: "This is useful for processes running in the background which do
  not want to cause lock contention" (a background git can wait on another's lock).

## Files

- `scripts/repository_scope.py`, `scripts/cleanup_worktrees.py`, `scripts/export_vault.py`,
  `scripts/memory_queue.py`, `scripts/query_memory.py`, `scripts/scheduled_nightly.py`
- `tests/test_every_git_call_has_a_deadline.py`, `tests/test_scheduled_nightly.py`
