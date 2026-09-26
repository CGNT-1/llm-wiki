# A hang bound keeps its length

Date: 2026-09-27. Audit 2026-09-27, finding B-7 (my regression from 3faea074).

## What was wrong

3faea074 renamed every literal `deadline=time.monotonic() + N` outside tests about time
to `SHORT_TIMEOUT` (30 s). Twenty-five of them were 60, 120 or 180 s: backups, Restic,
a hybrid search leg, doctor, a launch package. `tests/slow_machine.py` says a wait the
test expects to be kept is a hang bound and hang bounds come from `LONG_TIMEOUT`
(300 s); shortening them to 30 s adds flakiness on slow Windows runners.

## Decision

Every site whose original literal was longer than `SHORT_TIMEOUT` now names
`LONG_TIMEOUT` (found by pairing each file's deadlines with its version before
3faea074 — the files are unchanged since, so the pairing is exact; 25 sites in 16
files). A passing test is exactly as fast.

Recurrence: the guard `test_no_test_gives_real_work_a_literal_deadline` already
forbids new literal deadlines in such tests, so no literal is left for a later
rewrite to shorten; a new deadline chooses a named constant from the start.

## Source

- pytest documentation, Flaky tests, https://docs.pytest.org/en/stable/explanation/flaky.html
  (fetched 2026-09-26): "Overly strict assertions can cause problems with floating
  point comparison as well as timing issues."

## Files

- 16 test files under `tests/` (listed by `git show` of this commit)
