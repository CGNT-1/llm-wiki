# The daily log keeps one clock, and a claim says which instant it means

Date: 2026-09-27 (research done 2026-09-26 UTC). Audit 2026-09-27 C-5.

## What is true today (measured in the code)

- A claim's `observed_at` is built as `f"{date}T{block}Z"` from the daily file's
  name and the block heading `## [HH:MM:SS]` (`compile_memory.py`, and the
  `TimestampBlock` in `claims.py`). `claims.py` validates exactly that string.
- The headings are written by six writers on two clocks. Five use the machine's
  local wall clock: `post_tool_capture`, `user_prompt_capture`,
  `session_end_project_tag`, `mcp_server._log_decision` (all naive
  `datetime.now()`), and the capture flush (`flush_memory._capture_now`, aware
  local). The deferred flush in `memory_queue._manual_flush` alone writes UTC. The
  daily file's own day (`daily_log_append.append_daily`) is the local day.
- Session evidence and its backfill already file sessions under the local day, on
  purpose (`docs/research/2026-09-17-the-six-capture-corrections-the-first-round-left.md`):
  a UTC day filed the same session twice.
- The claim ledger is UTC-only: `_strict_rfc3339_utc` and the bitemporal reader's
  `_canonical_time` refuse any other offset.

So on a machine that is not on UTC two things are wrong: a day's file mixes two
clocks (the deferred flush), and every claim labels a local wall-clock time `Z`,
which moves bitemporal "as of" answers by the machine's offset. On the owner's
machine (`Etc/UTC`) both clocks agree and nothing stored is wrong.

## Sources

1. RFC 3339, §4.2–4.3 (https://www.rfc-editor.org/rfc/rfc3339):
   "Numeric offsets are calculated as 'local time minus UTC'. So the equivalent
   time in UTC can be determined by subtracting the offset from the local time.
   For example, 18:50:00-04:00 is the same time as 22:50:00Z." and "If the time in
   UTC is known, but the offset to local time is unknown, this can be represented
   with an offset of '-00:00'. This differs semantically from an offset of 'Z' or
   '+00:00', which imply that UTC is the preferred reference point for the
   specified time." — `Z` asserts UTC; a local reading labelled `Z` is false.
2. Python `datetime` documentation
   (https://docs.python.org/3/library/datetime.html): "Whether a naive object
   represents Coordinated Universal Time (UTC), local time, or time in some other
   time zone is purely up to the program" and "Because naive datetime objects are
   treated by many datetime methods as local times, it is preferred to use aware
   datetimes to represent times in UTC. As such, the recommended way to create an
   object representing the current time in UTC is by calling
   `datetime.now(timezone.utc)`." — the program must decide the clock once; six
   naive reads decided it six times.
3. RFC 5424 (syslog), §6.2.3 (https://www.rfc-editor.org/rfc/rfc5424): "The
   TIMESTAMP field is a formalized timestamp derived from [RFC3339]", with either
   `Z` or a numeric offset — an established log format that lets a record be read
   in local time only because the offset travels with it.

## Alternatives

- (a) Every heading in UTC. Makes `Z` true with no validator change. Costs: the
  owner reads UTC times in a diary kept for them; the daily day would no longer be
  the session-evidence day, reopening the double-filing the 2026-09-17 fix closed;
  on a non-UTC machine the file of the switch-over day mixes clocks.
- (b) Local time with its offset in the heading (`## [21:05:00+03:00]`). Most
  exact, but it changes the heading every reader parses (claims, compile evidence
  spans, archive, episode consolidation) — a format change across the vault.
- (c) Keep the local diary; the claim carries the true UTC instant. The one clock
  for writing is the machine's aware local time. The compile converts the block's
  local time to UTC with the zone rules for that date. The validator no longer
  demands `local + Z`; it demands that `observed_at` is UTC and differs from the
  block's local reading by a real zone offset (a whole quarter hour between
  −12:00 and +14:00, the IANA range). That check reads no machine zone, so a
  ledger stays valid after the machine moves.

## Decision

(c). It keeps the format every reader parses and the day convention capture and
backfill already share, needs no stored data rewritten, and makes the one
machine-read timestamp true. Every existing ledger still validates: its `Z` label
is the zero offset. One helper, `iso_time.local_now()`, is the only clock a daily
writer may read, and a test refuses a naive `datetime.now()` in them.

## Trade-offs, stated

- A heading carries no offset. In the one repeated hour of a daylight-saving
  change the compile picks the first reading (`fold=0`), up to one hour off; a
  compile run after the machine changed zone converts old blocks with the new
  zone. (b) would remove both and is the path if that ever matters.
- The evidence tie is now "same local reading, a real offset apart" rather than
  byte-equal. A claim can no longer be moved to another second of its block, but
  it can name the same reading at another real offset.
- Claims already written on a non-UTC machine keep their false `Z`: the offset in
  force when they were written is not recorded anywhere, so they are not rewritten.
