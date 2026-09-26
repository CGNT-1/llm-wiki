# A secret is redacted before it is cut

Date: 2026-09-27. Audit 2026-09-27, finding B-4 (first part; the class of C-6 of
2026-09-26, fixed then only for the tool line).

## What was wrong (reproduced)

A redactor recognises a secret by its whole shape — `ghp_` plus 20 characters, a PEM
block with its END line. Four places cut a text before redacting it, so a secret that
crossed the cut was judged by a fragment and kept: `session_evidence._clipped_report`
cut a subagent's report at 8 000 characters and the redaction ran later (a GitHub token
across the cut stayed partly visible); `query_memory._excerpt` and
`session_evidence._redacted_body` redacted a slice; the capture's raw-window fallback
(`_turns_head` / `_turns_tail`, when not one whole turn fits the window) kept bytes cut
inside a token.

## Decision

Redact the whole text, then cut: `_clipped_report`, `_excerpt` and
`_redacted_body` now do that (`REDACTION_SLACK_CHARS`, which only existed to cut first,
is removed; the record is still bounded by `_bounded`). A raw window cut inside a token
drops the fragment at the cut (`_whole_tokens_head` / `_whole_tokens_tail`), because
bytes past the window cannot be read to judge it.

Guard: `tests/test_a_secret_is_redacted_before_it_is_cut.py` — a token across the report
cut shows no part of itself; a window cut inside a token keeps no fragment; and no script
hands a redactor a sliced argument (found by AST, repository-wide). All three fail on the
previous code.

## Source (fetched 2026-09-27)

- OWASP Logging Cheat Sheet, https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html —
  "Perform sanitization on all event data to prevent log injection attacks e.g. carriage
  return (CR), line feed (LF) and delimiter characters (and optionally to remove
  sensitive data)", before the data is recorded.

Bug fix: the evidence is the reproduction above; one source.

## Files

- `scripts/session_evidence.py`, `scripts/query_memory.py`, `scripts/integration_adapter.py`
- `tests/test_a_secret_is_redacted_before_it_is_cut.py`
