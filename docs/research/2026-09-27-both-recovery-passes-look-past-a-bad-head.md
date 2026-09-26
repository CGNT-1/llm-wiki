# Both recovery passes look past a bad head

Date: 2026-09-27. Audit 2026-09-27, finding C-4.

## What was wrong

The nightly capture recovery runs two passes over capture intents. Adoption (ready
intents with no task) was fixed on 2026-09-17 to widen its window by the records it
skipped, so a head of bad records cannot hide the rest. The pending pass (intents whose
publisher died before marking them ready, added 2026-09-26) read one fixed window of
`limit` rows, oldest first: when those rows could not be finished — their file moved,
their fence still held — every half-published intent behind them waited for good.
Its cutoff was also written with `isoformat()`, which drops the fraction on a whole
second, and compared as text with the queue's `updated_at`, stored with six fraction
digits (the "one width" class).

## Decision

One loop, `capture_adoption._drain`, for both passes: read a window widened by the
skips so far, handle it, repeat until the bound is met, only skipped records remain, or
`MAX_SKIPPED_INTENTS_PER_PASS` is reached. The pending cutoff is written with
`timespec="microseconds"`, the queue's own width.

Guard: `tests/test_both_recovery_passes_look_past_a_bad_head.py` — three broken pending
records ahead of an intact one, limit 2: the intact one is finished and three are named
skips; the cutoff of a whole second carries six digits. Both fail on the previous code.

## Source (fetched 2026-09-27)

- Python documentation, `datetime.isoformat`, https://docs.python.org/3/library/datetime.html —
  "`YYYY-MM-DDTHH:MM:SS.ffffff`, if microsecond is not 0"; "`YYYY-MM-DDTHH:MM:SS`, if
  microsecond is 0"; `timespec='microseconds'` gives the full `HH:MM:SS.ffffff`.

Bug fix: the evidence is the code path and the test; one source.

## Files

- `scripts/capture_adoption.py`
- `tests/test_both_recovery_passes_look_past_a_bad_head.py`
