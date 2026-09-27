# A weekly that never finishes is seen

Date: 2026-09-27. Audit 2026-09-27, finding B-15.

## What was wrong (live, read-only)

The weekly pass had not succeeded since 2026-09-13; its own record (since 09-24)
held only a skip of 09-26. Doctor's "weekly never completed" check fired only when a
skip record existed, and "stale" only after a first recorded run. A weekly that never
starts, or is killed before it writes its result, left no record at all, and doctor
stayed quiet.

## Decision

Two clocks, each written once by the side that knows:
- the nightly's first success records `weekly_due_since` (from then on a weekly is
  due); no weekly run for more than the weekly period plus a day
  (`WEEKLY_FRESH_SECONDS`) after it reads "never completed";
- the weekly records `last_weekly_started_at` as it starts; a start older than the
  scheduler's own weekly limit (`SCHEDULER_LIMIT_HOURS["weekly"]`, the limit that
  kills it) with no result after it reads "started … and did not finish".

Alternative considered: infer from log files. Rejected: logs are disposable and an
absent log is exactly the case to catch.

## Sources (fetched 2026-09-27)

- Healthchecks.io documentation, https://healthchecks.io/docs/ — "It keeps silent as
  long as pings arrive on time. It raises an alert as soon as a ping does not arrive on
  time."
- Prometheus documentation, query functions, https://prometheus.io/docs/prometheus/latest/querying/functions/ —
  `absent()`: "This is useful for alerting on when no time series exist for a given
  metric name and label combination."
- Google SRE book, Monitoring Distributed Systems,
  https://sre.google/sre-book/monitoring-distributed-systems/ — "Your monitoring system
  should address two questions: what's broken, and why?"

Conclusion (mine): a scheduled job is watched by the absence of its result against an
expected time, not by the presence of an error it had no chance to write.

## Guard

`tests/test_a_weekly_that_never_finishes_is_seen.py` — due for nine days with no run,
and started seven hours ago with no result, are both named (both quiet on the previous
code); a weekly that finished after it started is quiet.

## Files

- `scripts/doctor.py`, `scripts/scheduled_weekly.py`, `scripts/scheduled_nightly.py`
- `tests/test_a_weekly_that_never_finishes_is_seen.py`
