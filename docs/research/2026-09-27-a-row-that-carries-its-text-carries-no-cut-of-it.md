# A row that carries its text carries no cut of it

Date: 2026-09-27. Audit 2026-09-27 C-16.

## What was wrong

Every `recall` row read from the generation carried `summary`: the first non-heading
line of the chunk, cut at 120 characters (`search_memory._first_prose_line`). The same
row carries the chunk itself in `content`, so the summary was the start of `content`
again, and often a sentence cut in the middle ("One-sentence summary: the nightly pass
may advance the checkout to the remote"). On the live vault on 2026-09-27, one
eight-row answer spent about 760 bytes (≈190 tokens by chars/4) on these fragments.

The generation does not store a page's own one-sentence summary, so a correct
summary cannot be given without reading every page at query time or changing the
generation schema.

## Sources (fetched 2026-09-27)

1. Anthropic, "Writing effective tools for agents" —
   <https://www.anthropic.com/engineering/writing-tools-for-agents>: "Tool
   implementations should take care to return only high signal information back to
   agents. They should prioritize contextual relevance over flexibility, and eschew
   low-level technical identifiers."
2. Google API Improvement Proposals, AIP-157 Partial responses —
   <https://google.aip.dev/157>: "Sometimes, a resource can be either large or
   expensive to compute, and the API needs to give the user control over which
   fields it sends back." Fields a reader does not need are not sent.
3. Elasticsearch reference, highlighting —
   <https://www.elastic.co/guide/en/elasticsearch/reference/current/highlighting.html>:
   "You can use the Search API's `highlight` parameter to retrieve the best-matching
   highlighted snippets from one or more fields in your search results". A search
   engine's snippet is the best-matching part, chosen for the query — not the first
   line of the text it already returns whole.

## Alternatives considered

- Keep the cut line: repeats `content`, often mid-sentence. Rejected.
- Read each hit's page at query time for its `One-sentence summary:` line: one extra
  file read per row on every recall, outside the generation the answer claims to come
  from. Rejected.
- Store the page summary in the generation: a schema change of the derived index,
  which needs the owner's sign-off; not needed to stop the repetition.
- Chosen: a generation row carries no `summary`; its text is `content`. A Markdown
  fallback row, which carries no `content`, keeps the page's own summary line.
  `search_memory._first_prose_line` is removed; its only consumer was this field.

## Effect

About 190 tokens fewer per eight-row recall answer on the live vault, with no text
lost: every removed character is in the same row's `content`.
