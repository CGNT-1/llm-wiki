# A secret in structure is redacted as structure

Date: 2026-09-27. Audit 2026-09-27, finding A-4 (A-2 of 2026-09-26 fixed one case, not
the class).

## What was wrong (reproduced)

The session capture redacted the raw transcript — JSON Lines — as text before parsing
it (`integration_adapter._capture_path_evidence`). A bare value after a credential name
is matched up to a separator, and inside serialized JSON the quote that ends the string
is not a separator: `{"command":"export PASSWORD=hunter2pass","description":"d"}`
became `{"command":"export PASSWORD=[REDACTED],"description":"d"}` — not JSON — and
`session_evidence` dropped that turn. `blackboard._append_jsonl` did the same to its own
records (`redact_secrets(json.dumps(record))`). And there were three separate walkers
for structured payloads: the queue's (which blanks secret-named keys), the event
envelope's (which did not), and none for transcripts.

## Alternatives considered

1. Teach the text rules every JSON escape. Rejected: a regex over serialized JSON will
   always meet a quoting case it did not foresee; A-2 already tried.
2. Chosen: parse, then redact each string leaf and blank every value under a
   secret-named key, then serialize. `secret_redact.redact_structure` is the one walker
   (moved from the queue with its key rule `is_secret_key`); `redact_jsonl` applies it
   per line and falls back to text redaction only for a line that is not JSON, so
   nothing unparsed is kept unredacted. The queue, the blackboard, the event envelope
   and the transcript capture all use it; the queue's copies are removed.

## Guard

`tests/test_a_secret_in_structure_is_redacted_as_structure.py`:
- the audit's transcript line stays JSON and loses its secret (fails on the old code);
- secret-named keys are blanked at any depth, in the walker and in an event envelope;
- no script calls `redact_secrets(json.dumps(...))` — the shape of the class, found by
  AST, not by a list (it catches the old blackboard line).

## Sources (fetched 2026-09-27)

- JSON Lines, https://jsonlines.org/ — "Each Line is a Valid JSON Value".
- RFC 8259, §7, https://www.rfc-editor.org/rfc/rfc8259#section-7 — "All Unicode
  characters may be placed within the quotation marks, except for the characters that
  MUST be escaped: quotation mark, reverse solidus, and the control characters (U+0000
  through U+001F)."
- OWASP Logging Cheat Sheet, https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html —
  "Authentication passwords, database connection strings, encryption keys and other
  primary secrets …" and "Access tokens" are to be "removed, masked, sanitized, hashed,
  or encrypted" before logging.

Conclusion (mine): a record must stay a valid line and lose its secrets; only a
structural pass guarantees both, because the quote and the backslash are syntax in the
text but not in the value.

## Files

- `scripts/secret_redact.py` (`redact_structure`, `redact_jsonl`, `is_secret_key`)
- `scripts/memory_queue.py`, `scripts/blackboard.py`, `scripts/event_envelope.py`,
  `scripts/integration_adapter.py`
- `tests/test_a_secret_in_structure_is_redacted_as_structure.py`,
  `tests/test_bad_input_is_refused_before_it_reaches_the_database.py`
