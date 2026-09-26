# An answer is fresh by its own sources

Date: 2026-09-27. Audit 2026-09-27 B-10.

## What was wrong

`recall` and `get_decisions` marked every signal of every answer `stale` when any
indexed source anywhere in the vault had changed since the generation was built. A
project's `state.md` is rewritten by sessions all day, so almost every answer
carried `stale` and the envelope's confidence ceiling of 0.6. The flag stopped
telling a good answer from a bad one.

## Sources (fetched 2026-09-27)

1. RFC 9110, HTTP Semantics, section 8.8.3 and 8.8.1 —
   <https://www.rfc-editor.org/rfc/rfc9110.html#name-etag>:
   "An entity tag is an opaque validator for representing a selected representation
   of a resource." and "A validator is a representation metadata value that can be
   used to choose a selected representation when evaluating conditional requests."
   A validator belongs to the representation that was served, not to the whole origin.
2. RFC 9111, HTTP Caching, section 4.2 — <https://www.rfc-editor.org/rfc/rfc9111.html>:
   "A 'fresh' response is one whose age has not yet exceeded its freshness lifetime.
   Conversely, a 'stale' response is one where it has." Freshness is a property of
   one stored response.
3. Elasticsearch reference, near real-time search —
   <https://www.elastic.co/guide/en/elasticsearch/reference/current/near-real-time.html>:
   "A refresh makes all operations performed on an index since the last refresh
   available for search." and "By default, Elasticsearch periodically refreshes
   indices every second…". A search engine accepts that its index trails its writes
   and does not call every hit stale because some document was written since.

## Alternatives considered

- Keep vault-wide staleness (status quo): every answer stale most of the day. Rejected.
- Judge only the answer's cited sources: a note compiled after the build, which the
  index cannot find, would never make an answer stale — the 2026-09-24 failure
  ("a page compiled at 11:20 was not found for the rest of the day while `recall`
  said fresh") would return. Rejected.
- Chosen: an answer is stale when a source it cites changed or vanished since the
  build (the RFC 9110 view: the validator of what was served), or when the set of
  compiled notes changed (a note added, edited or removed — knowledge the index
  cannot see yet and that may answer the question). Project `state.md`/`context.md`
  that the answer does not cite no longer count: they are rewritten continuously as
  session handoff, and the answer's age is already stated by `index_timestamp`.
- When the generation's source manifest cannot be read, the answer is `unknown`,
  not `stale` or `fresh`: every generation binds exactly one source manifest, so an
  unreadable one means freshness cannot be judged.

## Trade-off

An uncited project file that changed after the build might now match the query; the
answer does not say so. Notes still carry that signal, because they change only when
a compile writes them.
