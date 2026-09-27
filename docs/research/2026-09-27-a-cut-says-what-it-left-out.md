# A cut says what it left out

Date: 2026-09-27. Law 9, phase 2b: the class-d limits of `docs/LIMITS-2026-09-27.md`
(a bound that drops items), in the modules outside the phase-2a set.

## Requirement

Law 9: a limit needs a stated basis, and law 6 forbids hiding a problem. A bound that
drops items must either not lose data or say that it dropped some.

## Sources

- Language Server Protocol 3.17, `CompletionList.isIncomplete`: "This list is not
  complete. Further typing should result in recomputing this list."
  https://microsoft.github.io/language-server-protocol/specifications/lsp/3.17/specification/
- GitHub REST API, pagination: "When a response is paginated, the response headers will
  include a `link` header." and "If the endpoint does not support pagination, or if all
  results fit on a single page, the `link` header will be omitted."
  https://docs.github.com/en/rest/using-the-rest-api/using-pagination-in-the-rest-api
- OpenTelemetry common specification, attribute limits: "There MAY be a log emitted to
  indicate to the user that an attribute was truncated, discarded, or replaced due to a
  limit." https://opentelemetry.io/docs/specs/otel/common/

All three separate the cut from its disclosure: the answer may be partial, but it says
so. None keeps data that is stored for later use behind a silent cap.

## Decisions (per site)

Lost data, cap removed (the real bound is elsewhere and already loud):
- `episode_consolidation.MAX_ITEMS = 8`: lessons past the eighth were dropped though
  the prompt never asked for at most eight. The answer's size is bounded by
  `CONSOLIDATION_MAX_TOKENS`; every grounded lesson is written.
- `ledger.MAX_RECORDS_PER_TURN = 8`: the ledger exists so code counts things; a ninth
  record in one turn was dropped and the count came out low. The prompt states no cap;
  the reply is bounded by the call's `max_tokens` (1500 per batch).
- `provenance_join.MAX_NOTES_SCANNED = 500`: notes after the 500th alphabetically were
  never searched. The scan now covers every note, bounded by the caller's deadline and
  the existing per-note 256 KiB bound, and the answer states `page_count`,
  `pages_truncated` and `scan_complete`.
- `repository_worktrees.MAX_WORKTREES_PER_REPOSITORY = 64`: worktrees past the 64th in
  git's listing were never discovered for indexing. The listing is already bounded by
  `repository_index.MAX_GIT_OUTPUT_BYTES` (refused loudly), and the work per pass by
  `MAX_FOLLOWED_PER_PASS` and the deadline.

Display cuts, now disclosed:
- `code_graph` argument flows (`FLOW_MAX_ROWS`) and paths (`PATH_MAX_ROWS`): the answer
  states `flows_truncated`/`flow_count` and `paths_truncated`.
- `retrieval_disposition.MAX_PRINTED_PAGES`: the printout ends with how many more.

Already disclosed or a stated contract (basis written beside the constant): the
`code_graph` seed/community/hotspot/caller limits, `impact_symbols`, `repository_index`,
`installed_memory_repair`, `evidence_graph_builder`, `code_extractor`, `build_guardrails`,
`backfill_sessions`, `code_navigation`, `session_evidence` (truncation note in the
record); `fact_keys.MAX_KEYS_PER_TURN`, `refusal_pass.MAX_QUERIES` and
`aggregation_pass.MAX_FANOUT` repeat the number the prompt asks for.

## The two left after phase 2b

- `code_hints.MAX_ROUTE_MATCHES = 5` (removed): a dependency answer named at most five
  other checkouts serving one `METHOD path` and dropped the rest without a mark. Its
  own comment called five such services "a misconfiguration worth reading about" —
  the case where the full list matters most. `find_routes` now returns every match;
  each hint file already holds at most `MAX_HINT_ROUTES` routes, and the dependency
  walk has its own row limit.
- `symbol_snippet._definition_lines` cut the definitions found in one file to five,
  and `_matching_nodes` cut the matched nodes to five, so `resolved_nodes` reported the
  cut count, never the true one. `MAX_LOCATIONS = 5` stays as a display bound (each
  snippet is up to 120 lines), stated above the constant; the answer now carries the
  true `resolved_nodes` plus `nodes_omitted` and `snippets_omitted`, following the
  `*_omitted` convention of the other answers (`rows_omitted`, `members_omitted`).
  `definition_sites` still shows at most five sites and returns a bare list, so it
  cannot say what it left out without a change to its callers in `code_graph` and
  `mcp_server`; recorded here, not done.

Guard: `tests/test_a_route_and_a_snippet_say_what_they_left_out.py` (3 tests, all
three fail on the code before this change).
