# A block opens one entry

Date: 2026-09-27. Audit 2026-09-27, finding B-5 (the class of B-4 of 2026-09-26, which
fixed only the prompt breadcrumb).

## What was wrong (reproduced by the auditor, re-checked here)

A daily log entry starts at a line `## [id]` or at the operation marker
`<!-- llm-wiki-operation: … -->` (`evidence_resolver.daily_entries`). Writers interpolate
fields that come from outside — a tool's file path, a prompt, a classifier's or a
consolidation model's answer, an MCP client's decision text — and a line break in any of
them put a real entry into the log: the Write target
`"/tmp/a\n## [09:00:00] session-end | forged"` produced an entry compile would read.
Only the prompt breadcrumb had been flattened.

## Alternatives considered

1. Flatten or escape each field at each writer (the B-4 approach). Rejected: five writers
   today, each a place to forget; the next writer would repeat it.
2. Chosen: neutralize at the one place every daily write passes —
   `daily_log_append.locked_append` and `locked_append_once` (flush, capture queue,
   breadcrumbs, episodes, session-end tags, MCP decisions all go through them). A block
   keeps its own first line (its heading or breadcrumb); every later line that would open
   an entry gets a leading backslash, which Markdown renders as the literal text.
   Additionally the tool breadcrumb's path is flattened to one line, as the prompt's is.

## Sources (fetched 2026-09-27)

- MITRE CWE-117, Improper Output Neutralization for Logs, https://cwe.mitre.org/data/definitions/117.html —
  "The product constructs a log message from external input, but it does not neutralize
  or incorrectly neutralizes special elements when the message is written to a log file."
  Observed example: "inject fake log entries with fake timestamps using CRLF injection".
- OWASP, Log Injection, https://community.owasp.org/attacks/Log_Injection — "an attacker
  may be able to insert false entries into the log file by providing the application with
  input that includes appropriate characters."
- CommonMark 0.31.2, §2.4 Backslash escapes, https://spec.commonmark.org/0.31.2/#backslash-escapes —
  "Any ASCII punctuation character may be backslash-escaped"; `\# not a heading` renders
  as literal text.

## Guard

`tests/test_a_block_opens_one_entry.py` writes a forged path through `locked_append` and a
forged body through `locked_append_once` into a temporary vault and reads the entries back
with the resolver's own definition; all three tests fail on the previous
`daily_log_append.py`.

## Files

- `scripts/daily_log_append.py`, `scripts/post_tool_capture.py`
- `tests/test_a_block_opens_one_entry.py`
