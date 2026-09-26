# An ownership failure says what and when

Date: 2026-09-26 (audit of 2026-09-27, item B-8).

## What was true

- The Windows navigation job failed once in about 33 runs (`main`, run
  36252530355): the `timeout` ownership scenario measured nothing. The note of
  2026-09-26 (`docs/research/2026-09-26-an-ownership-probe-says-why-it-measured-nothing.md`)
  began naming a reason, but five failure points raised a bare `RuntimeError`
  (`_check_probe_error`, `_require_single_terminal` twice, `_prepare_process`
  twice), so each read `RuntimeError` or `RuntimeError:<cause>`; the message was
  dropped; and `_recover_ownership_scenario` ran the reset under a suppress of
  every exception, so a failed reset left no trace and the next attempt started
  from an unknown state.
- That job runs Python 3.10 (`tests.yml`, pyright-navigation matrix). The probe's
  timeout budget is `_OWNERSHIP_TIMEOUT_SECONDS = 0.05`, read on
  `time.monotonic()`, and dispatch is polled with `_OWNERSHIP_POLL_SECONDS =
  0.001`.

## Sources

1. PEP 418 (https://peps.python.org/pep-0418/, read 2026-09-26): on Windows
   `time.monotonic()` uses `GetTickCount64()`; its table gives OS resolution
   16 ms and Python resolution 15 ms on Windows Seven.
2. What's New in Python 3.13 (https://docs.python.org/3/whatsnew/3.13.html, read
   2026-09-26): "On Windows, `monotonic()` now uses the
   `QueryPerformanceCounter()` clock for a resolution of 1 microsecond, instead of
   the `GetTickCount64()` clock which has a resolution of 15.6 milliseconds."
3. Microsoft, `timeBeginPeriod`
   (https://learn.microsoft.com/en-us/windows/win32/api/timeapi/nf-timeapi-timebeginperiod,
   read 2026-09-26): "Setting a higher resolution can improve the accuracy of
   time-out intervals in wait functions"; since Windows 10 2004, "For processes
   which have not called this function, Windows does not guarantee a higher
   resolution than the default system resolution."

## What follows, and what does not

- Fact: on the CI job's Python, a 50 ms deadline is read on a clock that moves in
  15.6 ms steps, and a 1 ms wait lasts at least one timer period. The effective
  budget is roughly 34-66 ms, and the dispatch poll runs about every 15.6 ms
  instead of every 1 ms.
- Not established: that this caused the failure. On Linux (1 us clock) every
  `timeout` attempt in three instrumented runs was measured; there is no Windows
  reproduction. Changing the budget, the poll, or the product's deadline clock
  without evidence would trade one guess for another, and a longer budget makes
  the server answer first (`raced`) more often.

## Decision

- The five failure points raise `_OwnershipProbeError` with their own code:
  `wrong_terminal`, `not_sent`, `no_single_terminal`, `no_prior_request`,
  `no_live_process` (plus `:<cause type>` when there is a cause).
- Each unmeasured attempt keeps its message, the cause's message, how long the
  attempt ran (`perf_counter`, high resolution on every platform), and the
  resolution of the monotonic clock. The report's error entry carries it in an
  optional `message` field, added to
  `benchmark/code-navigation-python-report-v1.schema.json`.
- A failed reset is recorded and, for a scenario that ended unmeasured, reported
  as `ownership:<scenario>:recovery` with its own code and message. The suppress
  is gone.
- Guard: `tests/test_an_ownership_failure_says_what_and_when.py`, including an
  AST check that no ownership-probe failure is a bare `RuntimeError` and nothing
  in the runner suppresses exceptions. Its four tests fail on the old runner.

The next Windows failure names which step failed, after how many milliseconds,
on what clock. That evidence decides the budget question; until then the root
cause stays open.
