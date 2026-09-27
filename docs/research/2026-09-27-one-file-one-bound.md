# One file, one bound

Date: 2026-09-27. Audit 2026-09-27, finding B-3.

## What was wrong (reproduced by the auditor)

A capture decision file — the classifier's answer stored twice (the wire answer and the
operation plan) plus metadata — had four size bounds written as literals: the writer
(`flush_memory`) and two readers allowed 1 MiB, the semantic-decision indexer
(`MemoryQueue._read_semantic_decision_bytes`) 64 KiB. A 43 KB answer made an 89 KB
decision: written, then refused by the indexer on every retry with a `PermissionError`
naming the file as not "bounded", until the attempts were spent. The session record in
`raw/sessions` survived; the daily summary was lost. CLI providers do not enforce the
1 500-token request, so such answers do occur.

## Decision

One constant, `reliable_memory.MAX_CAPTURE_DECISION_BYTES` (1 MiB, the writer's bound,
basis written beside it), used by the writer and all three readers. Not capping the
answer itself: cutting a model's summary to fit a reader would be the crutch; the file is
already bounded where it is written.

Guard: `tests/test_one_file_one_bound.py` — a 90 KB decision is indexed (fails on the old
code), and every runtime read inside a function about a decision in `memory_queue` and
`flush_memory` uses that one constant (found by AST).

## Source (fetched 2026-09-27)

- "Don't repeat yourself", https://en.wikipedia.org/wiki/Don%27t_repeat_yourself —
  "Every piece of knowledge must have a single, unambiguous, authoritative representation
  within a system."

Bug fix: the evidence is the reproduction; one source.

## Not closed

CLI providers still ignore the requested token cap; an answer over 1 MiB is refused with
its named error. The flush prompt's own `1500` request stays as it was.

## Files

- `scripts/reliable_memory.py`, `scripts/flush_memory.py`, `scripts/memory_queue.py`
- `tests/test_one_file_one_bound.py`
