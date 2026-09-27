# A reader is cancelled until it leaves

Date: 2026-09-27. Scope: `scripts/lsp_protocol.py` (`LspProtocol.close`, `_stop_io`,
`_abort_startup`), `pyproject.toml` (`faulthandler_timeout`).

## What happened (fact)

CI run 36312497314, job `windows_full py3.13-s2` (PR #45 head 44517ee9, LSP code
unchanged since main b8d8b121): the progress artifact's last started test is
`tests/test_lsp_protocol.py::test_close_unblocks_native_pipe_reader_and_stops_owners`;
no test finished between 10:56:47 and 11:44:13, when GitHub cancelled the job. The same
test passed on the other Windows jobs of that run and on Linux. An earlier silent
Windows death (run 34727708815, 2026-09-13, py3.11-s2 after 2 058 of 2 080 tests, no
traceback) may be the same defect; that is not shown.

## Cause (inferred from code and sources, not reproduced — no Windows machine here)

On Windows the reader thread reads a pipe with one blocking `FileIO.read`
(`select()` takes only sockets there). `close()` then did, in order: mark closed, one
`CancelSynchronousIo` on the reader thread, close the reader stream, join with a
deadline. Two facts make that close unbounded:

1. A cancel issued before the reader's `ReadFile` starts finds nothing and is lost —
   the code treated `ERROR_NOT_FOUND` as success. The reader passes its "stopped?"
   check, the cancel misses, the reader enters `ReadFile`, and the pipe's writer never
   writes (the test's peer is idle; a real server may be too).
2. CPython's `FileIO.read` and `close` call the C runtime's `read()`/`close()` on the
   descriptor, and the UCRT holds the descriptor's lock for the whole `_read` — including
   the blocking `ReadFile` — while `_close` takes the same lock. So the closing thread
   waits for the read, which waits forever. The deadline-bounded join is never reached;
   that matches 48 minutes without a finished test.

## Sources

- Microsoft, CancelSynchronousIo: "If this function cannot find a request to cancel,
  the return value is 0 (zero), and GetLastError returns ERROR_NOT_FOUND." and "The
  CancelSynchronousIo function does not wait for all canceled operations to complete."
  https://learn.microsoft.com/en-us/windows/win32/fileio/cancelsynchronousio-func
- UCRT source (as shipped with the Windows SDK; mirror
  https://github.com/huangqinjin/ucrt): `lowio/read.cpp` — `_read` calls
  `__acrt_lowio_lock_fh(fh)` and then `_read_nolock(fh, buffer, buffer_size)` inside the
  locked block, unlocking in `__finally`; `lowio/close.cpp` — `_close` runs
  `__acrt_lowio_lock_fh_and_call(fh, ...)` around `_close_nolock_internal`.
- CPython, `Python/fileutils.c` (3.13), `_Py_read`: `n = read(fd, buf, (int)count);`
  — the C runtime call above.
- pytest, "How to handle test failures": "The faulthandler_timeout=X configuration
  option can be used to dump the traceback of all threads if a test takes longer than X
  seconds to finish." https://docs.pytest.org/en/stable/how-to/failures.html

## Decision

- A stream whose owner thread is alive inside a descriptor read or write is not closed
  by another thread on Windows; its owner closes it in its own `finally` on the way out
  (both owner loops already do). Sockets are still shut down, which unblocks them.
- `close()` and a failed start re-issue the cancel until the owner leaves, waiting on the
  owner's exit (`join`) between attempts, never past the close deadline. A cancel that
  is lost to the race is followed by one that finds the read. If the owner still does
  not leave, the existing deadline join raises "LSP protocol owner did not stop before
  deadline" instead of hanging.
- The two platform facts are named constants (`_CLOSE_WAITS_FOR_A_READ`,
  `_PIPES_HAVE_NO_SELECT`), which is what lets the Linux test drive the Windows path.

Rejected: skipping the test on Windows (hides a hang a real server can hit); a sleep
before the cancel (narrows the race, does not close it); closing the OS handle directly
under the CRT (the descriptor table would then name a closed handle).

## Guards

- `tests/test_lsp_protocol.py::test_a_lost_cancel_is_repeated_and_a_read_stream_is_never_closed_under_its_reader`:
  a pipe whose close records being called during a read, and a cancel that is lost the
  first time. With the old close order restored (mutation check) it fails with
  `closed_during_read = True`.
- `faulthandler_timeout = 600` in `pyproject.toml`: basis — the slowest legitimate test
  of the last green main run (36260843078, 88 470 test cases in 36 jobs) took 384.9 s;
  600 s is about 1.5 times that and inside the 60-minute Windows job limit. Any future
  hang dumps every thread's stack into the CI log.

## Unverified until Windows CI

The fix on a real Windows pipe; that `CancelSynchronousIo` issued while the owner is in
`ReadFile` ends it with ERROR_OPERATION_ABORTED under the UCRT lock (Microsoft documents
the cancel; the lock only delays close, not the cancel).

## Second finding: the fake server's peer re-raised a failed send at close

Fact: the clean full run on e02e4a76 (Linux, under load) ended
`tests/test_lsp_protocol.py::test_fatal_callback_runs_once_and_fails_all_pending_once`
with an ERROR at teardown: `BrokenPipeError [Errno 32]` from `FakeLspServer.close` →
`FakeLspPeer.close` → `writer.close()`. Seen 2 of 15 runs under load, 0 of 30 idle on
both 44517ee9 and e02e4a76, so not a law-5 regression.

Cause (reproduced deterministically, idle): the peer wrote through `sock.makefile("wb")`.
When a send meets a client that already left, `flush()` raises and the bytes stay in the
buffer; `close()` flushes again and raises the same error a second time — in teardown,
after the handler had already met and absorbed it as a disconnect. In the flaky test the
handler's second frame is sent after the test ended and teardown closed the client, which
only happens when the handler thread is delayed by load.

- Python `io`: `IOBase.close()` — "Flush and close this stream."; `BufferedWriter` —
  "data is normally placed into an internal buffer. The buffer will be written out ...
  when the BufferedWriter object is closed or destroyed."
  https://docs.python.org/3/library/io.html
- Python `socket.sendall()`: "this method continues to send data from bytes until
  either all data has been sent or an error occurs." — nothing is retained after an
  error. https://docs.python.org/3/library/socket.html

Fix: `FakeLspPeer.send_raw` sends with one `sendall` under the write lock, and the
buffered writer is gone; `close()` closes the reader and the socket without sending.
A real handler error still reaches `FakeLspServer.failures` and is raised by `close()`
as before. Guard: `test_a_peer_closes_cleanly_after_its_client_left` — on the old peer
it fails with `BrokenPipeError` from `close()`.

## Follow-up: a closed stream has no descriptor (2026-09-27)

CI run 36327902173 (PR #45 at 313dba83) failed 17 Windows jobs: every LSP close raised
`ValueError: I/O operation on closed file`, and the owners left behind then exhausted
the startup cleanup registry (901 cascading errors). Cause: on Windows the owner now
closes its own stream, and `_descriptor_of` asked that already closed stream for
`fileno()`. Python's io documentation: "Once the file is closed, any operation on the
file (e.g. reading or writing) will raise a ValueError", while `fileno()` documents only
"An OSError is raised if the IO object does not use a file descriptor." The helper
caught OSError and AttributeError, not ValueError. The path is gated by
`_CLOSE_WAITS_FOR_A_READ`, false on Linux, so no Linux run reached it.

Fix: a closed stream has no descriptor (`ValueError` joins the caught errors).
Guard: `tests/test_lsp_protocol.py` runs every case through both close paths
(`posix-close`, `windows-close`) on every platform. On the unfixed code the Windows
path fails on Linux too: 5 failed, 42 errors; fixed: 308 passed. With the Windows
close path forced on, the 14 suites that failed on Windows CI pass on Linux (715).
Real Windows remains the final check.
