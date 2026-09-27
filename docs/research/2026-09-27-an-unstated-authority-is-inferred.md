# An unstated authority is inferred

Date: 2026-09-27. Audit 2026-09-27, finding C-15.

## What was wrong

`provenance.authority_weight` gave a source with no `source_authority` the neutral
weight 1.0 — the same as `ai-derived`, above `inferred` (0.8) and `session` (0.9).
CLAUDE.md rule 13 says the opposite: "Without them, pages default to medium /
inferred and lose ranking." A page that never said where its claim came from
outranked one honestly labelled `inferred`. Four live notes have no label.

## Alternatives considered

1. Change `DEFAULT_AUTHORITY_WEIGHT` to 0.8. Rejected: every code file, daily log and
   project file states no authority, so all of them would drop against every
   labelled note — a code question would lose its code.
2. Backfill `source_authority` into the pages. Rejected: it writes a claim about the
   page nobody made.
3. Chosen: `provenance.page_authority(stated, path)` — a compiled knowledge page
   (`knowledge/notes/`) that states nothing ranks as `inferred`; every other source
   keeps what it states, or nothing (neutral). `authority_weight` and `trust_weight`
   now take the source's path as a required argument, so no ranking path (fusion,
   rerank, generation rows, dense rows, the Markdown fallback, page facts) can leave
   the default out.
4. Rejected after a first attempt: writing `inferred` into the page's metadata. The
   grounded-answer rule (`query_memory._is_quotable`) refuses `ai-derived` and
   `inferred` sources as quotable evidence, so the metadata change would also have
   stopped unlabelled notes from being quoted — a change of what may ground an
   answer, not only of ranking. That is the owner's decision; the default here is
   applied to ranking only, and the page's own label is left as it is.

Test fixtures that silently relied on "no label = neutral" while testing something
else (fusion, co-activation, history, the public search path) now state
`ai-derived` explicitly; what they test is unchanged.

## Sources (fetched 2026-09-27)

- OKF v0.2, https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md —
  "No `verified` key → unverified"; "A concept with no trust frontmatter is still
  consumable; consumers MUST NOT reject it." Absence lowers trust; it does not reject.
- Wikipedia:Verifiability, https://en.wikipedia.org/wiki/Wikipedia:Verifiability —
  "Facts or claims without an inline citation to a reliable source that directly
  supports them may be removed."
- W3C PROV-DM, https://www.w3.org/TR/prov-dm/ — "Attribution is the ascribing of an
  entity to an agent." Without an attribution there is no agent to credit, which is
  what `inferred` names.

## Guard

`tests/test_an_unstated_authority_is_inferred.py`: an unlabelled note weighs as
`inferred`, a labelled one as labelled, code and daily logs stay neutral; the
Markdown fallback ranks with the same default. The required path argument is the
recurrence guard: a new call site cannot omit it.

## Files

- `scripts/provenance.py`, `scripts/search_memory.py`, `scripts/retrieval.py`,
  `scripts/reranker.py`, `scripts/page_facts.py`
- test fixtures: `tests/test_retrieval.py`, `tests/test_session_evidence.py`,
  `tests/test_the_six_capture_corrections_the_first_round_left.py`,
  `tests/test_what_was_mentioned_together.py`, `tests/test_what_carried_an_answer_is_remembered.py`
- `tests/test_an_unstated_authority_is_inferred.py`
