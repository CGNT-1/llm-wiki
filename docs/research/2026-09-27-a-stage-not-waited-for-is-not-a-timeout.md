# A stage not waited for is not a timeout

Date: 2026-09-27. Audit 2026-09-27, finding B-9.

## What was wrong

The optional stages (dense retrieval, the cross-encoder rerank) are refused a wait
when their measured cost does not fit the window a question has left: the worker
still runs to warm the model, only the caller does not wait. That refusal raised the
same `OptionalStageTimeout` as a real timeout, so every such answer said
`fallback_reason: optional_stage_timeout` and, for the rerank, `partial: true` —
although nothing timed out and no candidate was lost (a rerank only reorders).
Measured by the auditor on the live vault under load (load average 9–21 on four
cores): warm rerank cost 7.95 s against a window of about 3.5–5 s, so every recall
carried the false label.

## Alternatives considered

1. Keep one label and document it. Rejected: the label is read as "something ran out
   of time", which is not what happened, and `partial` makes the answer look
   incomplete.
2. Turn the reranker off by default. Not decided here: whether it pays for itself is
   a measurement on an idle machine, not a code change; the auditor's number was
   taken under heavy load. Left to the owner with the data below.
3. Chosen: `OptionalStageNotAdmitted` (a subclass, so every existing handler still
   catches it) carries `reason = "optional_stage_not_admitted"` and
   `partial = False`; a real timeout keeps `optional_stage_timeout` and
   `partial = True`. The rerank trace records the stage's own reason; a dense leg
   that did not run is still partial either way, because its candidates are missing.

## Sources (fetched 2026-09-27)

- Google SRE book, Handling Overload, https://sre.google/sre-book/handling-overload/ —
  "One option for handling overload is to serve degraded responses: responses that
  are not as accurate as or that contain less data than normal responses, but that
  are easier to compute."
- gRPC, Deadlines, https://grpc.io/docs/guides/deadlines/ — once a client's deadline
  passes "the client will give up and fail the RPC with the DEADLINE_EXCEEDED status";
  a deadline exceeded is a distinct outcome from a call that was never waited for.
- OpenTelemetry, Traces, span status, https://opentelemetry.io/docs/concepts/signals/traces/#span-status —
  "A span status that is Unset means that the operation it tracked successfully
  completed without an error." "When a span status is Error, then that means some
  error occurred in the operation it tracks."

Conclusion (mine): a trace must say which of these happened — degraded by choice,
ran out of time, or failed — because each asks for a different action.

## Guard

`tests/test_a_stage_not_waited_for_is_not_a_timeout.py`: a rerank known not to fit is
`optional_stage_not_admitted` and not partial, through the real admission and the
real rerank trace. Fails on the previous code.

## Files

- `scripts/retrieval.py`, `docs/USER-GUIDE.md`
- `tests/test_a_stage_not_waited_for_is_not_a_timeout.py`
