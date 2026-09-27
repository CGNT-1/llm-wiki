# A signal handler writes without a buffer

Date: 2026-09-27. Scope: `tests/fake_lsp_server.py`, the setsid-descendant fixture
behind `tests/test_lsp_process_tree.py::test_setsid_escape_is_outside_posix_process_group_containment`.

## What failed

The clean full run of 2026-09-27 failed this test once with "process-tree fixture
closed stdout while still running"; the same test passed 5 of 5 times alone. A
stress harness (the fixture spawned 300 times, SIGTERM sent to its group as soon as
its `descendant_pid` line arrived, four busy loops on the four cores) lost the
fixture 150 times out of 300, every time with the same last stderr line:
`RuntimeError: reentrant call inside <_io.BufferedWriter name='<stdout>'>`.

The fixture's SIGTERM handler called `print(..., flush=True)`. The test reads the
`descendant_pid` line and signals at once, so the signal can land while the main
thread is still inside the `print` that wrote that line. The handler then enters the
same buffered writer and Python raises, the fixture dies, and the test sees end of
stream. Load widens that window, which is why only the full run met it.

## Sources

- Python, `io` — Reentrancy: "Binary buffered objects (instances of BufferedReader,
  BufferedWriter, BufferedRandom and BufferedRWPair) are not reentrant. While
  reentrant calls will not happen in normal situations, they can arise from doing
  I/O in a signal handler. If a thread tries to re-enter a buffered object which it
  is already accessing, a RuntimeError is raised."
  https://docs.python.org/3/library/io.html
- Python, `signal`: "A Python signal handler does not get executed inside the
  low-level (C) signal handler. Instead, the low-level signal handler sets a flag
  which tells the virtual machine to execute the corresponding Python signal handler
  at a later point (for example, at the next bytecode instruction)." and "If a signal
  handler raises an exception, the exception will be propagated to the main thread
  and may be raised after any bytecode instruction."
  https://docs.python.org/3/library/signal.html
- Linux man-pages, signal-safety(7): "An async-signal-safe function is one that can
  be safely called from within a signal handler." `write(2)` is on the POSIX list;
  the stdio functions are not, because they keep buffers with counters and indexes
  that a handler may find half-updated.
  https://man7.org/linux/man-pages/man7/signal-safety.7.html

## Alternatives

1. The handler writes its record with one `os.write` to the stdout descriptor: no
   buffer, no lock, the same bytes. Chosen. Every earlier `print` in the fixture
   flushes, so nothing buffered can be overtaken.
2. The handler only sets a flag and the main loop reports it. The main loop is
   blocked in `stdin.readline()`, so it would need a `select` loop or
   `signal.set_wakeup_fd` — more code for the same record.
3. Retry or widen the test's wait. Rejected: the fixture is dead, no wait brings the
   record back; it would only hide the defect (law 6).

## Guard

A test walks every Python file in `scripts/` and `tests/`, finds each function
registered with `signal.signal`, and fails if its body calls `print` or writes
through `sys.stdout`/`sys.stderr`. It fails on the fixture as it was.
