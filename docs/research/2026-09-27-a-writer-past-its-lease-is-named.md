# A writer past its lease is named

Date: 2026-09-27. Audit 2026-09-27, item C-3 (the release-retry part).

## The finding

A Markdown writer that finishes releases its hold on the global writer gate.
When the database is busy, the release is retried in a background thread: soon,
then once a minute for about an hour (`_RELEASE_RETRY_DELAYS`, audit
2026-09-26 A-13). After the last try the thread returns silently. The row in
`writer_owners` stays, its heartbeat has stopped, and its process is still
alive, so the registry — which reclaims only a dead owner — never frees it.
Every other writer waits until that process exits. `doctor` counted the row as
one more "live writer", which is normal, so nothing was said.

The same state is left by any holder that stops heartbeating while alive — a
hung writer, a heartbeat thread that died — not only by an exhausted retry.

## Sources (fetched 2026-09-27)

1. Wikipedia, "Lease (computer science)" (after Gray and Cheriton, 1989) —
   https://en.wikipedia.org/wiki/Lease_(computer_science). A lease grants a
   right "for a limited period"; one not renewed "automatically expires,
   making the resource available for reallocation". A holder past its term
   has broken the lease's own promise.
2. Martin Kleppmann, "How to do distributed locking" (2016) —
   https://martin.kleppmann.com/2016/02/08/how-to-do-distributed-locking.html.
   A holder that keeps running past its lease is the dangerous case; safety
   comes from fencing, which the gate already has. What remains is noticing.
3. Google SRE book, "Monitoring Distributed Systems" —
   https://sre.google/sre-book/monitoring-distributed-systems/. Monitor what
   is broken (the symptom) as well as why; the symptom here is a gate held by
   a lease that expired.

## Alternatives

- Log a line when the retry gives up. Names one cause of the symptom, and
  only if someone reads the log; rejected as the only signal.
- Retry forever. Hides the symptom longer; rejected.
- Let the registry reclaim an expired live owner. Changes the ownership
  contract (a live owner may still be writing); out of scope and not safe
  without the owner's decision.
- **Chosen:** `doctor` counts every writer row whose process is alive and whose
  lease has expired (`overdue_writers`), reports the transactions check as
  degraded, and says in the message that other writers wait. It names the
  symptom whatever caused it, from state already on disk, with no new file.

## Trade-offs

A writer whose heartbeat is late by a moment can be caught in a snapshot and
named once; the lease is the stated promise, so being past it is the finding.
The status is `degraded`, not `error`: writes are delayed, nothing is lost.
