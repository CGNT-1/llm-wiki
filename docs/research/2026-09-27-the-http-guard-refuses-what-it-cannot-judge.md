# The HTTP guard refuses what it cannot judge

Date: 2026-09-27. Audit 2026-09-27, finding C-14.

## What was wrong (reproduced)

- A bearer token with a non-ASCII character reached `hmac.compare_digest` as a
  non-ASCII `str` and raised `TypeError`; under uvicorn that is a 500 with a logged
  traceback, not a 401.
- Every scope that was not `http` passed the guard unchecked. A WebSocket reached the
  inner app; it was harmless only because the mounted route happened to be HTTP-only.

## Alternatives considered

1. Catch `TypeError` around the comparison. Rejected: it hides a class (any type
   mismatch) behind a special case.
2. Refuse non-ASCII headers early. Rejected: the header is already decoded as
   Latin-1; the comparison should simply be on bytes.
3. Chosen: compare the Latin-1 bytes of both sides; let `lifespan` through (the app
   needs it to start), close a WebSocket before accepting it, and ignore any other
   scope type — only HTTP is served.

## Sources (fetched 2026-09-27)

- Python, hmac.compare_digest, https://docs.python.org/3/library/hmac.html — "a and b
  must both be of the same type: either str (ASCII only, …), or a bytes-like object."
- ASGI HTTP & WebSocket spec, https://asgi.readthedocs.io/en/latest/specs/www.html —
  a close sent before the socket is accepted means "the server must close the
  connection with a HTTP 403 error code (Forbidden), and not complete the WebSocket
  handshake".
- RFC 6750 §3.1, https://www.rfc-editor.org/rfc/rfc6750#section-3.1 — `invalid_token`:
  "The access token provided is expired, revoked, malformed, or invalid for other
  reasons. The resource SHOULD respond with the HTTP 401 (Unauthorized) status code."

## Guard

`tests/test_the_http_guard_refuses_what_it_cannot_judge.py`: a non-ASCII token is a
401; a WebSocket never reaches the app and is closed with 1008. Both fail on the
previous code.

## Files

- `scripts/mcp_http.py`
- `tests/test_the_http_guard_refuses_what_it_cannot_judge.py`
