# A rollback undoes only what it did

Date: 2026-09-28. Scope: `scripts/install_control.py`, the v2 update path of `install.sh` /
`install.ps1` (`install_control.py install`) and its rollback.

## What failed

On the owner's machine Claude-27, `bash ./install.sh` over an existing v2 install started an
`update` transaction that ended `quarantined` with `{'code': 'install_rollback_drift'}` at
2026-09-28T15:06:36Z. Resource states: `unix-profile`, `systemd-user-maintenance`,
`opencode-plugin` verified (written), `claude-user-settings` **pending** (never written),
`codex-user-hooks` reverted. Every later `install.sh` and `install_control.py rollback` then
failed with `install_transaction_blocks_new_work`: no way forward and no way back.

Reproduced on Claude-30 in a sandbox (copied `run/install`, paths rewritten to a scratch
HOME, `systemctl` stubbed): the systemd unit files there were changed outside the installer
on 2026-09-13. `install_control.py install` failed forward on `systemd-user-maintenance`,
then quarantined with `install_scheduler_projection_conflict`; the record of that resource
was still `pending`; `rollback` then answered `install_transaction_blocks_new_work`.

## Cause (read in the code, reproduced)

1. `_v2_apply_resource` refuses a resource whose owned projection is neither the previously
   installed value nor the new one (`install_resource_drift`, or the scheduler's projection
   conflict). That refusal is correct: someone else changed a file we manage.
2. `_v2_failed_operation` then reverts **every** record in reverse order, including those
   still `pending`. `_v2_revert_resource` demands that a resource sit at what this
   transaction wrote or at its rollback value; a pending resource that drifted sits at
   neither, so the revert raises the same drift and the transaction is quarantined.
3. The quarantine code overwrote the forward failure (`error.code` became the rollback's
   code), so the record no longer said why the install failed.
4. `rollback` treats a quarantined `update` as a settled state and goes through the active
   manifest's health, which reports the quarantine, so the operator's only command refuses.

## Sources

- Microsoft, Rollback Installation (Windows Installer): "When the Windows Installer processes
  the installation script ... it simultaneously generates a rollback script and saves a copy
  of every file deleted during the installation. ... If however the installation is
  unsuccessful, the installer automatically performs a rollback installation that returns the
  system to its original state." The rollback script is built *as actions run*: it undoes
  what was performed. https://learn.microsoft.com/en-us/windows/win32/msi/rollback-installation
- Debian Policy, ch. 6 maintainer scripts: "if a major error occurs ... the actions are, in
  general, run backwards"; scripts must be idempotent so that when "called again, it doesn't
  bomb out or cause any harm, but just ensures that everything is the way it ought to be";
  a failed configuration leaves the package "Half-Configured" and a rerun repairs it.
  https://www.debian.org/doc/debian-policy/ch-maintainerscripts.html
- PostgreSQL, WAL introduction: recovery works from the log of changes made — "any changes
  that have not been applied to the data pages can be redone from the WAL records"; nothing
  the log did not record is touched. https://www.postgresql.org/docs/current/wal-intro.html

## Decision

- A revert undoes only what the transaction did: a record still `pending` was never written,
  so it is marked `reverted` without reading or writing its file. Records `mutating` or
  `verified` are reverted with the existing checks (they only write a file still holding what
  this transaction wrote).
- The forward failure stays in the record: `error.code` is the rollback's failure when the
  rollback fails, and `error.cause` keeps the forward code.
- `rollback` retries the revert of a quarantined `install`/`update` transaction. It is the
  same bounded revert, idempotent in Debian's sense: it writes only files that still hold what
  the installer wrote, so a retry after the operator has inspected the machine cannot overwrite
  anyone's edit; a resource that really drifted after our write keeps the transaction
  quarantined and is named by its record.

- A retried revert also skips a record already `reverted`: an earlier attempt settled it,
  and its file may have been edited since. Without this the retry reached the pending record
  it had just marked `reverted` and refused it again (found by the regression test).
- `--adopt <resource-id>` on `install.sh`, `install.ps1` and `install_control.py install`
  is the operator's explicit decision about a refused file: the update takes the resource
  over as it is now and records that content as its rollback point, so a failed update or a
  later `rollback` returns the file to exactly what the operator adopted. A committed
  rollback now reverts to the value the update recorded (`rollback`), which is the previous
  release's value for every resource not adopted. Adoption is refused for a scheduler
  (`install_adopt_unsupported`): its projection says which rendered definition is
  installed, so a hand-edited unit has no representation to keep. An id the install does
  not manage is refused (`install_adopt_unknown_resource`). This follows Debian's
  configuration-file rule, "local changes must be preserved during a package upgrade"
  (Debian Policy §10.7.3, https://www.debian.org/doc/debian-policy/ch-files.html): an
  adopted file is written only with the operator's consent, and its content is kept as the
  rollback point, so a failure or a `rollback` returns it exactly.

Rejected: overwriting a drifted file (loses a user's or another tool's edit, law 6);
clearing the quarantine by hand-editing `run/install/transaction.json` (no check at all);
treating drift as success (masking).

## Consequence for the owner

After this change, the rollback of a failed update no longer quarantines on a resource it
never touched, and an existing quarantine is left by `install_control.py rollback`. The
update itself still refuses a resource changed outside the installer, and now says which
(the `pending`/`mutating` record and `error.cause`); that file needs the owner's decision.
