# A dead task counts until it is resolved

Date: 2026-09-27. Audit 2026-09-27, finding B-13 (my B-23 fix of 2026-09-26 hid what
it was written to show).

## What was wrong (live, read-only)

Doctor counted only dead queue tasks that died within 7 days. All 25 live dead tasks
died 08-27..09-08, so the queue read healthy while 25 captures stayed unresolved. The
7-day window assumed the weekly purge exports older ones — but the weekly had not run
since 09-13 (B-15).

## Decision

Every dead task in the queue counts (`dead_unresolved`) until it is redriven or the
weekly purge exports it past the retention window; the age of the oldest is reported
(`oldest_dead_days`) and never used to hide. `DEAD_TASK_LIVE_SECONDS` and the
recent-only helper are removed.

## Sources (fetched 2026-09-27)

- Amazon SQS Developer Guide, dead-letter queues,
  https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-dead-letter-queues.html —
  "DLQs are useful for debugging your application because you can isolate unconsumed
  messages to determine why processing did not succeed."
- Enterprise Integration Patterns, Dead Letter Channel,
  https://www.enterpriseintegrationpatterns.com/patterns/messaging/DeadLetterChannel.html —
  "When a messaging system determines that it cannot or should not deliver a message,
  it may elect to move the message to a Dead Letter Channel."
- Google SRE book, Monitoring Distributed Systems,
  https://sre.google/sre-book/monitoring-distributed-systems/ — "Your monitoring system
  should address two questions: what's broken, and why?"

Conclusion (mine): a dead letter is kept to be looked at; its age says how long it has
waited, not that it stopped mattering.

## Guard

`tests/test_a_failure_in_the_night_is_named.py::test_every_dead_task_counts_and_the_oldest_age_is_shown`
— a 1-day and a 30-day dead task both count, oldest 30 days (the previous code counted 1).

## Files

- `scripts/doctor.py`, `tests/test_a_failure_in_the_night_is_named.py`
