# A backup snapshots what hooks write

Date: 2026-09-27. Audit 2026-09-27, finding B-16. Owner decision 2026-09-27: "Снимок
на момент чтения" (recorded with `log_decision`).

## What was wrong (reproduced by the state-layer fork)

The Restic backup scans the vault and `run/`, copies, then scans again and refuses with
`source_changed` if anything differs. The session hooks write `run/state.json` and
create files under `run/capture-intents/` on every tool call, and they are not fenced by
the backup's owner lease (a hook never waits). One state write during the copy refused
the backup, so with any agent running a backup was impossible.

## Alternatives

1. Make the hooks wait for the backup. Rejected by the owner: capture would stall or be
   deferred for the whole copy.
2. Chosen: the hook-written runtime paths (`state.json`, `state.json.previous`,
   `capture-intents/`) are left out of the "nothing changed" scan and copied in a
   separate step as a snapshot at read time: every file through one open descriptor,
   a file gone since its directory was listed is skipped, a non-regular entry is still
   refused. `state.json.lock` is not copied. Everything else keeps the exact
   scan-copy-rescan check. Trade-off: the copy holds the hook state as read, not as at
   the end of the copy.

## Sources (fetched 2026-09-27)

- rename(2), https://man7.org/linux/man-pages/man2/rename.2.html — "If newpath already
  exists, it will be atomically replaced, so that there is no point at which another
  process attempting to access newpath will find it missing."
- unlink(2), https://man7.org/linux/man-pages/man2/unlink.2.html — "If the name was the
  last link to a file but any processes still have the file open, the file will remain
  in existence until the last file descriptor referring to it is closed."
- restic documentation, Backing up, https://restic.readthedocs.io/en/stable/040_backup.html —
  "Files are read from the VSS snapshot instead of the regular filesystem. This allows
  to backup files that are exclusively locked by another process during the backup."

Conclusion (mine): `state.json` is written by atomic replace, so an open descriptor
holds one whole version even if the name is replaced mid-read; reading a live file as
a point-in-time snapshot is the same compromise backup tools make for data other
processes keep writing.

## Guard

`tests/test_a_backup_snapshots_what_hooks_write.py`: a hook rewriting `state.json` and
filing a new intent during the copy no longer refuses the backup, and the copied state
is one whole version (fails on the previous code with `staging_copy_mismatch`); the
hooks' lock file is not copied. The existing race test still requires a changed vault
file to refuse the backup.

## Files

- `scripts/private_vault_backup.py`
- `tests/test_a_backup_snapshots_what_hooks_write.py`
