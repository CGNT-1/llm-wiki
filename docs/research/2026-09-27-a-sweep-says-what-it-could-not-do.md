# A sweep says what it could not do

Date: 2026-09-27. Audit 2026-09-27, findings C-2 and C-3 (state part).

## What was wrong

- C-2: `MAX_KNOWLEDGE_ENTRIES = 200_000` in `reclaim_runtime_state.py` counted files
  that matched `.*.tmp`, not the walk over `knowledge/`, so it bounded nothing, and no
  basis was ever given for the number (my own addition of 2026-09-26).
- C-3: `_remove` turned every `OSError` into "0 bytes", so a staged file that could not
  be removed vanished from the nightly report and from the failure list.

## Alternatives considered

1. Keep a count bound but count directories. Rejected: still a number without a basis.
2. Chosen: bound the walk by the reclaim step's own deadline (the one the image and
   history prunes already use); a late walk reports `unfinished` and the next night
   continues. A file that went away (`FileNotFoundError`) is not a failure; every other
   `OSError` is counted and named, and reaches `_failures`, which the night report and
   the step's exit already read.

## Sources (fetched 2026-09-27)

- PEP 20, The Zen of Python, https://peps.python.org/pep-0020/ — "Errors should never
  pass silently." "Unless explicitly silenced."
- Python documentation, built-in exceptions,
  https://docs.python.org/3/library/exceptions.html#FileNotFoundError —
  FileNotFoundError: "Raised when a file or directory is requested but doesn't exist."
  IsADirectoryError: "Raised when a file operation (such as os.remove()) is requested
  on a directory." PermissionError: "Raised when trying to run an operation without the
  adequate access rights".
- Google SRE book, Monitoring Distributed Systems,
  https://sre.google/sre-book/monitoring-distributed-systems/ — "Your monitoring system
  should address two questions: what's broken, and why?"

Conclusion (mine): only the absent file is an expected outcome of a race; the other
`OSError`s are what is broken, and the report must say which file and why.

## Guard

`tests/test_a_sweep_says_what_it_could_not_do.py` — an orphan that cannot be removed
is a named failure next to one that was; the knowledge walk past its deadline removes
nothing and says `unfinished`; a sweep failure reaches the night's failure list. All
three fail on the previous code.

## Files

- `scripts/reclaim_runtime_state.py`
- `tests/test_a_sweep_says_what_it_could_not_do.py`, `tests/test_runtime_state_is_reclaimed.py`
