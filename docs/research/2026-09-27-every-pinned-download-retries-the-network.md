# Every pinned download retries the network

Date: 2026-09-27. Audit 2026-09-27, finding C-10.

## What was wrong

`install_language_server` retries a transient network error since 2026-09-23 (CI run
35926589114 ended on one TCP reset). `install_pyright` — installed on every CI run of
the `pyright-navigation` jobs — did not: `_download_artifact` turned any `OSError` into
`pyright_download_failed`, and `_next_download_chunk` did the same to a reset in the
middle of the stream, so even a retry wrapper could not have told a reset from a refusal.

## Decision

- `_download_artifact` runs the whole download through the shared
  `pinned_download.retry_transient` (same class of transient errors, same waits, same
  deadline). Each attempt starts at the beginning of the file (`_seek_start`): the
  pinned artifact is identical every time, so a complete attempt writes at least as far
  as a partial one, and the digests verify what was kept.
- `_next_download_chunk` lets a mid-stream `OSError` through; `_download_artifact` names
  it `pyright_download_failed` only after the last attempt.
- Guard: `tests/test_every_pinned_download_retries_the_network.py` — a reset after the
  first chunk is fetched again and the install succeeds (fails on the old code); and any
  script that opens a pinned URL or calls `download_pinned` must use `retry_transient`.

Alternative considered: a fresh temporary file per attempt — rejected, the temporary is
owned by `_install_under_lock` for its whole life and a second owner would split cleanup.

## Sources (fetched 2026-09-27)

- Google Cloud Storage, Retry strategy, https://docs.cloud.google.com/storage/docs/retry-strategy —
  retry "HTTP 408, 429, and 5xx response codes. Socket timeouts and TCP disconnects."
- RFC 9110 §15.6.4, https://www.rfc-editor.org/rfc/rfc9110.txt — "The 503 (Service
  Unavailable) status code indicates that the server is currently unable to handle the
  request due to a temporary overload or scheduled maintenance, which will likely be
  alleviated after some delay."
- Python documentation, Built-in Exceptions, https://docs.python.org/3/library/exceptions.html —
  ConnectionResetError: "A subclass of ConnectionError, raised when a connection is reset
  by the peer. Corresponds to errno ECONNRESET." (a reset is an `OSError`, the class the
  retry checks, until something converts it).

## Files

- `scripts/install_pyright.py`
- `tests/test_every_pinned_download_retries_the_network.py`
