# A read-only doctor says what it touches

Date: 2026-09-27. Audit 2026-09-27, finding C-1.

## What was wrong

`run_doctor` said it mutates "only with repair=True", the README said doctor "is
read-only", and `test_read_only_run_never_attempts_a_write` claimed no write. But the
filesystem check always runs `reliable_memory._sqlite_lock_probe`, which creates one
SQLite file in the state root, takes locks from two connections and removes it. The
test patched only `os.open`, so the write below it was invisible. The auditor rightly
refused to run doctor on the live vault on the strength of that claim.

## Alternatives considered

1. Skip the probe without `--repair`. Rejected: whether two connections really exclude
   each other cannot be learned without trying, and the nightly and agents run doctor
   without repair; the check would silently go to "unknown" everywhere.
2. Probe somewhere outside the state root. Rejected: the question is about this
   filesystem, and any other place is still a write.
3. Chosen: keep the probe and state the contract exactly — doctor changes no state; its
   locking probe creates and removes one temporary file. The docstring and the three
   READMEs say so; a new test snapshots the whole tree, hidden entries and directories
   included, before and after a read-only run and requires them equal; the old test is
   renamed to what it proves (no Python-level file write).

## Sources (fetched 2026-09-27)

- SQLite, How To Corrupt An SQLite Database File, §2.1, https://www.sqlite.org/howtocorrupt.html —
  "SQLite depends on the underlying filesystem to do locking as the documentation says
  it will. But some filesystems contain bugs in their locking logic such that the locks
  do not always behave as advertised."
- SQLite, SQLite Over a Network, https://www.sqlite.org/useovernet.html — "SQLite relies
  on exclusive locks for write operations, and those have been known to operate
  incorrectly for some network filesystems."
- Wikipedia, Principle of least astonishment,
  https://en.wikipedia.org/wiki/Principle_of_least_astonishment — "a component of a
  system should behave in a way that most users will expect it to behave".

Conclusion (mine): the probe is the only real test of locking, so it stays; what must
change is the promise, so that nobody is surprised by the one file it touches.

## Files

- `scripts/doctor.py` (docstring), `README.md`, `README.ru.md`, `README.zh-CN.md`
- `tests/test_doctor.py`
