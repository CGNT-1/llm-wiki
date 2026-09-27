# A rerank has the window it was measured to need

Date: 2026-09-27. Audit 2026-09-27 B-9: the cross-encoder reranker is on by default,
but on the MCP path its warm cost did not fit the window it was offered, so most
answers came back without it.

## Measured (this machine, 4 cores, CPU; load average recorded per block)

Latency — the product's own `reranker.rerank` (bge-reranker-v2-m3, int8 dynamic,
512 tokens, depth 10), ten real vault notes per query, 45 queries (44 warm):

| run | load before → after | cold load | first call | warm p50 | warm p95 | max | ≤ 3.5 s | ≤ 5 s | peak RSS |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 1.40 → 4.11 | 11.6 s | 11.9 s | 4.14 s | 9.61 s | 10.0 s | – | – | 2.8 GB |
| 2 | 3.48 → 4.37 | 8.9 s | 3.8 s | 3.46 s | 5.68 s | 9.71 s | 55 % | 89 % | 2.8 GB |
| depth 5 | 3.85 → 3.81 | – | 4.9 s | 1.97 s | 5.04 s | 5.2 s | 86 % | 93 % | 2.8 GB |

(The measurement itself keeps four cores busy; "idle" means no other job ran.)

Quality — `benchmark/retrieval-v2-crosslingual.json` (42 answerable queries, 27
cross-language), first stage the product encoder (multilingual-e5-small through
`onnx_encoder`), then the product reranker; MRR@10 / nDCG@10, gold from the
corpus, no manual labels:

| arm | all MRR | all nDCG | cross MRR | cross nDCG | mono MRR |
|---|---|---|---|---|---|
| no rerank | 0.658 | 0.722 | 0.506 | 0.604 | 0.933 |
| rerank depth 5 | 0.814 | 0.836 | 0.710 | 0.758 | 1.000 |
| rerank depth 7 | 0.838 | 0.856 | 0.748 | 0.789 | 1.000 |
| rerank depth 10 | 0.880 | 0.889 | 0.814 | 0.840 | 1.000 |

## What the window was

An MCP call had `MCP_OPERATION_SECONDS` = 10 s, a default with no measurement behind
it. The hybrid run stops a reserved second early, and an optional stage may take
half of what is left and never the last 2.5 s (`retrieval._optional_stage_deadline`),
so the rerank is offered about 3.5–4 s. Admission compares that with the last
observed cost: at depth 10 about half the calls rerank (55 % of warm costs fit 3.5 s).
Expected cross-language MRR on the MCP path: 0.55 × 0.814 + 0.45 × 0.506 ≈ 0.68 at
depth 10, and 0.86 × 0.710 + 0.14 × 0.506 ≈ 0.68 at depth 5 — the same; a shallower
rerank buys nothing.

## Sources

- sentence-transformers, Retrieve & Re-Rank: "Cross-Encoder achieve better
  performances than Bi-Encoders. However, for many application they are not practical
  as they do not produce embeddings." and "First, you use an efficient Bi-Encoder to
  retrieve e.g. the top-100 most similar sentences for a query. Then, you use a
  Cross-Encoder to re-rank these 100 hits".
  https://www.sbert.net/examples/cross_encoder/applications/README.html
- Google SRE book, Service Level Objectives: "a high-order percentile, such as the 99th
  or 99.9th, shows you a plausible worst-case value, while using the 50th percentile
  (also known as the median) emphasizes the typical case." and "people typically
  prefer a slightly slower system to one with high variance in response time".
  https://sre.google/sre-book/service-level-objectives/
- Claude Code, MCP: an unset `MCP_TOOL_TIMEOUT` means "its default of about 28 hours";
  the client does not bind a tool call to 10 s. https://code.claude.com/docs/en/mcp
- sentence-transformers, efficiency: "ONNX models can be quantized to int8 precision
  using Optimum, allowing for faster inference on CPUs." (the product already runs int8).
  https://sbert.net/docs/cross_encoder/usage/efficiency.html

## Decision

Keep the reranker on by default (law 4: +0.31 cross-language MRR for about 3.5 s of
CPU, no tokens; a better first answer saves re-queries). Give the two tools whose
answer goes through it — `recall` (not grounded) and `get_decisions` — a budget sized
from the measured high percentile instead of the median: `mcp.retrieval_seconds` =
14 s, so the rerank window is about 0.5 × (14 − 1.0 − 0.5) ≈ 6.25 s, above the warm
p95 of 5.68 s. It depends on the machine (the audit measured 7.95 s under load), so
it is a setting (law 9) an operator on a slower machine raises; every other tool keeps
10 s. Cost: a recall that reranks waits for it (median 3.5 s) instead of answering
without it half the time.

Alternatives: depth 5 (same expected quality on the MCP path, rejected); turning the
reranker off (loses 0.31 cross-language MRR); an adaptive depth by observed cost (more
machinery for the same expected result; not needed while one budget fits).

Not measured: the first call after a cold start still does not fit (9–12 s load); the
MCP warm-up and the straggler that finishes it make the next call warm, as before.
