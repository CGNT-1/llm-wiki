# An update costs what it says

Date: 2026-09-27. Audit 2026-09-27, finding C-13 (the rest of C-13 of 2026-09-26).

## What was wrong (read in the code)

- `_fast_forward_over` put the identical untracked copies back only on
  `SelfUpdateError`; a `subprocess.TimeoutExpired` or `OSError` from the merge skipped
  `_put_back`, so the set-aside files stayed deleted until the next update.
- The cost comment counted "two fetches" and `WORST_CASE_SECONDS` added two fetch
  timeouts; the code fetches once. The worst case the nightly sums was 120 s high.

## Decision

- Any failure of the merge — `BaseException` — puts the copies back. `_put_back` writes
  only a path that is missing, so a merge that got as far as the file is left alone.
- `FETCHES_PER_UPDATE = 1`, and the comment lists the calls the code makes.
- Guard: `tests/test_an_update_costs_what_it_says.py` runs a real update against a real
  clone and counts the git commands it ran: exactly `FETCHES_PER_UPDATE` fetches and
  `GIT_CALLS_PER_UPDATE` other calls, so the bound cannot drift from the code again; and
  a merge that times out leaves the copy in place.

## Source

- Python documentation, subprocess.run, https://docs.python.org/3/library/subprocess.html
  — "If the timeout expires, the child process will be killed and waited for. The
  TimeoutExpired exception will be re-raised after the child process has terminated."
  (A timeout is an exception of its own class, not a failed return code.)

## Files

- `scripts/self_update.py`
- `tests/test_an_update_costs_what_it_says.py`, `tests/test_a_pass_that_knows_how_long_it_can_be.py`
