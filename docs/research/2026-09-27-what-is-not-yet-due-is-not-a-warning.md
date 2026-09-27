# What is not yet due is not a warning

Date: 2026-09-27. Audit 2026-09-27, finding raised while fixing the installer order.

## The problem (facts, read in the code and reproduced offline)

Right after a healthy fresh install, `doctor` reported:

- `backup: degraded, "No knowledge snapshot has been taken yet."`. `_backup_check`
  graded the absence of a snapshot the same way whether the vault was installed
  ten minutes ago or ten months ago.
- `pyright: degraded, pyright_missing`. Pyright is installed only by a separate,
  explicit operator action (`scripts/install_pyright.py`). A vault that never
  asked for it was told something is broken.
- `scheduler: skipped, "Nightly maintenance status is unknown."`. This does not
  degrade the overall status, but it has the opposite defect: it never escalates.
  A timer that never fires stays "unknown" forever.

Because `backup` and `pyright` were degraded, the final doctor check of the
installer turned every fresh install into "installed with warnings". No install
step can clear any of the three findings. An operator who sees a warning on every
install stops reading warnings.

## Sources

1. Kubernetes, *Configure Liveness, Readiness and Startup Probes*
   (kubernetes/website, `configure-liveness-readiness-startup-probes.md`):
   "The solution is to set up a startup probe with the same command, HTTP or TCP
   check, with a `failureThreshold * periodSeconds` long enough to cover the worst
   case startup time." and "If the startup probe never succeeds, the container is
   killed after 300s". The startup window is sized from the worst case, and it
   ends: absence of success after the window is a failure.
2. Healthchecks.io documentation, *Introduction* (check states): "**New**. A newly
   created check that has not received any pings yet. Each new check you create
   will start in this state." and "**Late**. The "success" signal is due but has
   not arrived yet. It is not yet late by more than the check's configured
   **Grace Time**." Only "**Down**. The "success" signal has not arrived yet, and
   the Grace Time has elapsed. When a check transitions into the "Down" state,
   SITE_NAME sends alert messages". Not yet due and within grace are distinct,
   quiet states.
3. Icinga 2 documentation, *Advanced Topics, Check Result Freshness*: "It is
   determined by the `check_interval` attribute and no incoming check results in
   that period of time." Freshness is judged against the interval the job is
   supposed to keep, not against the calendar.

The repository's own precedent is the `models` check. When semantic search is not
installed, it answers "ok, Semantic search is not installed; no model weights are
expected." It does not say "degraded".

## Alternatives considered

- **Suppress the three findings during install** (an install-mode flag or an
  ignore list in `sync_memory`). Rejected: it hides the same states the day after,
  when they may be real. Law 6 forbids masking.
- **Keep "New" forever, as Healthchecks.io does** for a check that has never been
  pinged. Rejected: the installed scheduler is ours. A nightly that never runs is
  exactly the failure doctor exists to show (audit 2026-09-27 B-15 is the same
  class for the weekly pass). Icinga's freshness rule and the Kubernetes startup
  window both end the grace period.
- **Grade from the install instant** (chosen). `run/install/manifest.json` records
  `committed_at` when the install committed. Before the first due time plus the
  longest a pass may take, "never ran" and "no snapshot yet" are *pending*: status
  ok, with the time by which it is due. After that, they are findings. Pyright
  absent from every discovery source is *not installed*: status skipped, with the
  install command. Pyright present but wrong still degrades.

## The windows and their basis (law 9)

- First nightly: one schedule period (the nightly runs daily) plus
  `SCHEDULER_LIMIT_HOURS["nightly"]`, the longest a pass may run before the unit
  stops it. Today that is 24 h + 4 h = 28 h. It is derived from that constant, so
  if the limit changes, the window changes with it. The steady-state
  `NIGHTLY_FRESH_SECONDS` (26 h) measures the gap between two completions, so it
  is too short for the first run: an install at 03:30 waits 23.5 h for the next
  03:00 and may then run for 4 h.
- First snapshot: `BACKUP_FRESH_SECONDS` (two days, a nightly period plus a day of
  grace, 2026-09-24). A vault younger than that has not yet missed a snapshot. A
  missing snapshot is graded like a snapshot taken at install time.
- Without an install manifest (a development checkout, tests, a vault that was
  never installed), nothing tells doctor when the clock started. The old answers
  stand: `unknown` for the scheduler, degraded for the backup.

## Trade-offs

- Rerunning the installer resets the clock, since `committed_at` is the latest
  install. On a vault whose timer is broken, that buys at most one more window of
  28 h before the finding returns. It never hides a failed pass: `failed` is still
  graded before any of this.
- A Pyright that was installed and whose disposable `cache/` was then deleted
  reads as "not installed" rather than "degraded". Doctor cannot tell the two
  apart, because the only install record lives in that cache. The message still
  names the install command.
