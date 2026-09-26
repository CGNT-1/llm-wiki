# A redrive keeps the decision its parent sealed

Date: 2026-09-26 (research), audit 2026-09-27 item B-14.

## The defect (reproduced)

A capture task that died after it published and indexed its semantic decision
left one `semantic_decisions` row for the intent and stage, sealed by its own task
id and its own link digest. `redrive` copies the task under a new id and re-signs
the capture link for the child, so the child's link digest differs and it holds no
seal. `indexed_capture_decision` compared the row with the child's binding: two
elements differed (`active.seal_digest` was `None` against the child's expected
seal, and `row.active_link_digest` was the parent's digest against the child's),
and the child's one second chance ended with `semantic_decision_conflict`.
Reproduced end to end through the real queue:
`tests/test_a_redrive_reuses_the_decision_its_parent_indexed.py` fails on the
unfixed code with that error.

Fixing only that check exposed the next step of the same defect: when the parent
had also committed the Markdown block before dying, the child replays the same
operation id, gets back the parent's committed transaction, and
`append_captured_knowledge` refused it with `capture append transaction
preconditions conflict`, because the stored capture binding names the parent.

Root cause: the decision is one per intent and stage, but every proof that the
decision may be used was tied to the task that made it, and a redrive is a
different task.

## Sources (read 2026-09-26)

1. AWS Step Functions, "Restarting state machine executions with redrive"
   (docs.aws.amazon.com/step-functions/latest/dg/redrive-executions.html):
   "When you redrive an execution, Step Functions continues the failed execution
   from the unsuccessful step and uses the same input. Step Functions preserves the
   results and execution history of the successful steps, which are not rerun when
   you redrive an execution."
2. Stripe API reference, "Idempotent requests"
   (docs.stripe.com/api/idempotent_requests): "Stripe's idempotency works by saving
   the resulting status code and body of the first request made for any given
   idempotency key, regardless of whether it succeeds or fails. Subsequent requests
   with the same key return the same result" and "The idempotency layer compares
   incoming parameters to those of the original request and errors if they're not
   the same to prevent accidental misuse."
3. Microsoft Learn, "Durable Orchestrations Overview"
   (learn.microsoft.com/azure/azure-functions/durable/durable-functions-orchestrations):
   "During the replay, if the code tries to call a function ... the Durable Task
   Framework consults the execution history of the current orchestration. If it
   finds that the activity already executed and yielded a result, it replays that
   function's result".

All three keep a completed step's recorded result for the retry instead of
running it again, and Stripe still refuses a reuse whose parameters differ.

## Alternatives considered

- **Delete the parent's decision and ask the model again.** Rejected: the
  parent may already have committed Markdown from that decision; a second, different
  answer would write a second block (the idempotency the decision exists for).
- **Seal the decision on intent and stage only, dropping the task id.** Rejected:
  any task holding the intent could then use it, including one outside the family;
  it also changes the stored digest of every existing seal.
- **Accept a decision sealed by a task in the child's `redrive_of` chain (chosen).**
  The sealer is found by the row's own link digest and its seal digest is
  recomputed; the child must hold the same intent, its own live link, and either no
  seal or the seal for this decision. The child then gets its own seal to the same
  decision (no second decision row), which the Markdown write requires. A replayed
  append accepts a committed transaction whose binding is a sealed ancestor's for
  the same decision, and nothing wider.

## Trade-offs

- The chain walk reads one `tasks` row per ancestor; chains are as long as the
  number of redrives of one task.
- A decision a task outside the chain sealed is still refused
  (`test_a_decision_sealed_outside_the_redrive_chain_is_refused`).
- No schema change: the child's seal uses the existing `semantic-decision` consumer
  kind.
