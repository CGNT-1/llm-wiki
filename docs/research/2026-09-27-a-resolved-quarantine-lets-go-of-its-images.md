# A resolved quarantine lets go of its images

Date: 2026-09-27. Audit 2026-09-27, finding B-2 (quarantine part).

## What was wrong (measured, read-only)

The image prune took only committed and discarded transactions. A quarantined one kept
its before/after images forever: on this vault 117 rows from 2026-08-22..09-07 held
60.8 MB, with no operator path and no removal condition. Most of them are resolved —
`doctor` already counts them as history because a retry committed or a commit created
the files they meant to create.

## Alternatives

1. An operator command that retires quarantines by hand. Rejected: the owner does no
   manual chores, and the rule for "resolved" already exists in code.
2. Prune every quarantine's images after the undo window. Rejected: an unresolved
   quarantine is the only evidence of work that may really be lost.
3. Chosen: the image prune also takes a quarantined row that the transaction rows alone
   show resolved — the retry lineage (parent chain, request identity) or the outcome
   (every file it meant to create was created by a commit). The row stays quarantined
   with `artifacts_pruned_at` set; doctor's count does not change. A compile quarantine
   resolved only by doctor's fourth proof (a later compile of the same day) is left
   alone, because that proof reads the staged files. The three row-based proofs moved
   from `doctor` into `transaction_lineage`, so the prune and the health check read one
   rule (`resolved_quarantines`); `repair_refused_appends` uses it too.

## Sources (fetched 2026-09-27)

- GDPR Article 5(1)(e), https://gdpr-info.eu/art-5-gdpr/ — "kept in a form which permits
  identification of data subjects for no longer than is necessary for the purposes for
  which the personal data are processed".
- Amazon SQS Developer Guide, dead-letter queues,
  https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-dead-letter-queues.html —
  "DLQs are useful for debugging your application because you can isolate unconsumed
  messages to determine why processing did not succeed."
- Enterprise Integration Patterns, Dead Letter Channel,
  https://www.enterpriseintegrationpatterns.com/patterns/messaging/DeadLetterChannel.html —
  "When a messaging system determines that it cannot or should not deliver a message, it
  may elect to move the message to a Dead Letter Channel."

Conclusion (mine): a refused unit is kept for diagnosis while its question is open; once
the rows show it answered, the bulky payload has no purpose left (the images hold
private content), while the small record keeps the history.

## Guard

`tests/test_a_resolved_quarantine_lets_go_of_its_images.py`: a quarantine whose retry
committed loses its images, keeps its row, and doctor still counts nothing unresolved
(fails on the previous code); an unresolved quarantine keeps its images.

## Files

- `scripts/markdown_transaction.py`, `scripts/transaction_lineage.py`, `scripts/doctor.py`,
  `scripts/repair_refused_appends.py`
- `tests/test_a_resolved_quarantine_lets_go_of_its_images.py`
