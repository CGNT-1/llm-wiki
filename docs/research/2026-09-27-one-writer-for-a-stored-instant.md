# One writer for a stored instant

Date: 2026-09-27. Audit 2026-09-27, finding C-18.

## What was wrong

`iso_time.utc_text` was introduced on 2026-09-26 as the one writer of the stored
instant (UTC, six fraction digits, `Z`), but four other modules kept their own copy
of the same expression (`operational_ownership._timestamp`, `blackboard._timestamp`,
`generation_catalog`, `retrieval_telemetry`), and doctor still wrote the v2
`maintenance_owners` stamps with a bare `isoformat()` (no fraction on a whole
second). The copies agreed today; nothing kept them agreeing.

## Decision

All five now call `utc_text`. Guard: `tests/test_every_stored_instant_has_one_width.py`
refuses any other module spelling `isoformat(timespec='microseconds').replace(...)`.

Not changed, on purpose: `memory_queue._timestamp` writes the same instant with
`+00:00` instead of `Z`; its column is compared only with its own stamps, and
mixing two suffixes in one existing column is exactly what RFC 3339 §5.1 warns
against, so it keeps one form. `trace_ingest` keeps its seconds-wide stamps in its
own table.

## Sources (fetched 2026-09-27)

- RFC 3339, §5.1, https://www.rfc-editor.org/rfc/rfc3339#section-5.1 — "Assuming that
  the time zones of the dates and times are the same (e.g., all in UTC), expressed
  using the same string (e.g., all "Z" or all "+00:00"), and all times have the same
  number of fractional second digits, then the date and time strings may be sorted as
  strings … and a time-ordered sequence will result."
- Wikipedia, Don't repeat yourself, https://en.wikipedia.org/wiki/Don%27t_repeat_yourself —
  "Every piece of knowledge must have a single, unambiguous, authoritative
  representation within a system".
- Python documentation, datetime.isoformat, https://docs.python.org/3/library/datetime.html
  (fetched 2026-09-26) — "YYYY-MM-DDTHH:MM:SS, if microsecond is 0".

## Files

- `scripts/operational_ownership.py`, `scripts/blackboard.py`, `scripts/generation_catalog.py`,
  `scripts/retrieval_telemetry.py`, `scripts/doctor.py`
- `tests/test_every_stored_instant_has_one_width.py`
