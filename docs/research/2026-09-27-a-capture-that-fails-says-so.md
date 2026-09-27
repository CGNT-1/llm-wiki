# A capture that fails says so

Date: 2026-09-27. Audit 2026-09-27, finding C-3 (capture part).

## What was wrong

Four capture steps failed without a trace:
- the prompt and tool hooks each had their own parser that turned malformed hook input
  into `{}` — the event was simply not captured;
- a prompt counter that could not be updated returned 0, so the twentieth-prompt capture
  was skipped;
- `_run_maintenance_command` (the session-start capture worker and queue drain) sent all
  output to /dev/null and ignored the exit code and a spawn failure;
- `spawn_compile_if_idle` errors were dropped at session start.

## Decision

- One parser, `capture_diagnostics.hook_object(raw, kind)`, for both hooks: empty input
  is not a loss; a non-JSON or non-object input is recorded in the capture-failure trail
  (which doctor reads) and read as `{}`. The two copies are removed.
- The counter failure is recorded (`prompt_counter`).
- The maintenance drains and the compile spawn write one line each to
  `logs/hook-errors.log` through one writer (`_log_hook_error`, also used by the
  checkpoint diagnostics now), naming the script, argument and exit code or error.

Guard: `tests/test_a_capture_that_fails_says_so.py` — each of the four paths leaves its
record; all four fail on the previous code.

## Source (fetched 2026-09-27)

- OWASP Logging Cheat Sheet, https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html —
  the events to record include "Input validation failures e.g. protocol violations,
  unacceptable encodings, invalid parameter names and values".

Bug fix: the evidence is the code paths and the tests; one source.

## Files

- `scripts/capture_diagnostics.py`, `scripts/post_tool_capture.py`,
  `scripts/user_prompt_capture.py`, `scripts/integration_adapter.py`
- `tests/test_a_capture_that_fails_says_so.py`
