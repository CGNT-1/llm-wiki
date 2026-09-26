# An answer without a provider is not fresh

Date: 2026-09-27. Audit 2026-09-27, finding C-19.

## What was wrong

`mcp_server._navigation_freshness` mapped `stale` to stale, three failure statuses to
unknown, and everything else — including `unsupported`, which has no answer at all,
and any status added later — to `fresh`. An answer that said "no language server
claims this file" was reported as fresh evidence.

## Decision

One table, `_NAVIGATION_FRESHNESS`, names every `NavigationStatus`: `ok` and
`partial` are fresh (computed from the current revision), `stale` is stale,
`unsupported` is `missing` (no provider answered), the rest unknown; a status the
table does not know is unknown, never fresh. Alternative rejected: add
`unsupported` to the unknown set — it would keep the "default is fresh" rule that
caused this.

## Sources (fetched 2026-09-27)

- RFC 9111 §4.2, https://www.rfc-editor.org/rfc/rfc9111#section-4.2 — a fresh
  response is one "whose age has not yet exceeded its freshness lifetime"; freshness
  is a property of a response that exists.
- RFC 9110 §8.8.3, https://www.rfc-editor.org/rfc/rfc9110 — "The \"ETag\" field in a
  response provides the current entity tag for the selected representation"; with no
  representation there is nothing to validate.
- OpenTelemetry, span status, https://opentelemetry.io/docs/concepts/signals/traces/#span-status —
  "A span status that is Unset means that the operation it tracked successfully
  completed without an error." Status is reported for what the operation did.

## Guard

`tests/test_an_answer_without_a_provider_is_not_fresh.py` iterates the
`NavigationStatus` enum: every status must be in the table, `unsupported` is
`missing`, and an unknown status is `unknown`. A status added to the enum without a
freshness fails it. Fails on the previous code.

## Files

- `scripts/mcp_server.py`
- `tests/test_an_answer_without_a_provider_is_not_fresh.py`
