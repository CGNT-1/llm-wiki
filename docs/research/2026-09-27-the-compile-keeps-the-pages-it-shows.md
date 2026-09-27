# The compile keeps the pages it shows

Date: 2026-09-27. Audit 2026-09-27 C-6, remainder: which existing pages the compile
draft shows the model. Decision: keep the current selection; no code change.

## What the selection is

`pack_compile_batches` ranks every non-daily page by BM25 over the words it shares
with the batch's days (`_ContextRanking`) and `_fitting_context` adds pages in that
order while the prompt stays inside the input budget, skipping a page that does not
fit and trying the next. On a copy of the live vault (212 notes) the shown context is
2–6 pages, 4–20 KB; the prompt is ~22–23 KB for a day of 2.5–10 KB. The model uses
the pages to reuse an existing slug (an `update`) instead of inventing a new one;
`_with_snapshot_actions` only maps an exact slug match.

## Measured (24 drafts, real provider, vault copy, 2026-09-27)

Six already compiled days of 3.5–10 KB (2026-08-20, 09-10, 09-12, 09-13, 09-14,
09-24), one draft each under four rules; `current` twice to see the model's own
spread. A created slug is counted as "like an existing page" when its word set
overlaps an existing slug's by Jaccard ≥ 0.5 (automatic, no labelling).

| rule | prompt KB | creates | like an existing page | updates |
|---|---|---|---|---|
| current (run 1) | 136.5 | 16 | 3 | 2 |
| current (run 2) | 136.5 | 12 | 3 | 1 |
| prefix: rank order, stop at the first page that does not fit | 119.9 | 21 | 4 | 1 |
| none: no pages | 41.7 | 32 | 6 | 0 |

- No pages cuts input by 69% and doubles the pages created: 0 updates, twice the
  near-duplicates (a new slug differing from an existing page's only by one plural).
  Quality loss.
- `prefix` saves 12%; on 2026-09-13 it dropped the low-ranked small page that the
  skip-and-continue fill had carried, and three new pages replaced the update both
  `current` runs made or declined. The difference is inside the model's spread
  between the two `current` runs (16 vs 12 creates), so the saving is not shown to be
  free; law 4 forbids taking it unproven.
- "Only pages the day names" (slug or title present in the day's text) selected no
  page on 5 of 12 sampled days and at most one on 8, close to the `none` case above;
  it was not drafted separately, so its cost is inferred, not measured.

## Sources

- Liu et al., *Lost in the Middle* (TACL 2024, arXiv 2307.03172): performance
  "significantly degrades when models must access relevant information in the middle
  of long contexts" — the reason to keep the context short and ranked.
- Chroma, *Context Rot* (2025): "even a single distractor reduces performance relative
  to the baseline (needle only), and adding four distractors compounds this degradation
  further." https://www.trychroma.com/research/context-rot
- Anthropic, *Effective context engineering for AI agents*: "good context engineering
  means finding the smallest possible set of high-signal tokens that maximize the
  likelihood of some desired outcome."
  https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents

The sources argue for less context; the measurement shows this context is not filler:
removing it costs the updates it exists for. The smallest set that keeps them is not
yet known and needs a larger sample than 24 drafts (each draft took 99–418 s).

## Found on the way (not fixed here)

- Even `current` creates near-duplicates the snapshot cannot catch, because it maps
  only exact slugs: a new slug that differs from an existing page's by one article
  ("the") appeared in both `current` runs. A
  normalized-slug match in `_with_snapshot_actions` is the likely fix.
- A draft through the Claude CLI took 99–418 s; with the default
  `MEMORY_LLM_TIMEOUT_S=90` the first probe ended as `provider_timeout`.

## Cost

24 drafts plus three probes: ~500 KB of prompt text, about 160–215 k input tokens at
the measured 2.3–3.1 bytes per token (the CLI reports no usage).
