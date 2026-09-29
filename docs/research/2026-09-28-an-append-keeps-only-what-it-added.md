# An append keeps only what it added

Date: 2026-09-28. Scope: `scripts/markdown_transaction.py` — the before/after images
every recoverable Markdown transaction keeps under `run/transactions/<id>/`.

## What is wrong (measured on the live vault, read-only, 2026-09-27/28)

The disk reached 98 % (1.2 GB free). `run/transactions/` held 9 804 transaction
directories, 3.1 GB. Of the 8 111 operations of 2026-09-27 still holding images, 7 026
were appends (the after-bytes start with the before-bytes: hook captures into
`knowledge/daily/<day>.md`, 1.4 MB that day, and project journals); their compressed
images took 2 584.5 MB, while the bytes they actually added were 9.67 MB in total. The
1 085 other operations took 4.8 MB. Each append stored the whole file twice (before and
after), so a day's image bytes grow with appends × file size — quadratically on a busy
day — and the 2-day undo window (the run/ deletion contract) forbids pruning them sooner.

## Sources

- SQLite, File Locking And Concurrency in SQLite Version 3: "Before making changes to
  any page of the database, the process writes the original content of that page into
  the rollback journal." and "The rollback journal also records the initial size of the
  database so that if the database file grows it can be truncated back to its original
  size on a rollback." https://www.sqlite.org/lockingv3.html
- SQLite, Write-Ahead Logging: "The WAL approach inverts this. The original content is
  preserved in the database file and the changes are appended into a separate WAL
  file." https://www.sqlite.org/wal.html
- Git, Packfiles: "When Git packs objects, it looks for files that are named and sized
  similarly, and stores just the deltas from one version of the file to the next."
  https://git-scm.com/book/en/v2/Git-Internals-Packfiles
- Linux ext4 administration guide: data=ordered — "All data are forced directly out to
  the main file system prior to its metadata being committed to the journal." versus
  data=journal — "All data are committed into the journal prior to being written into
  the main file system." https://docs.kernel.org/admin-guide/ext4.html
- truncate(2): "If the file previously was larger than this size, the extra data is
  lost." https://man7.org/linux/man-pages/man2/truncate.2.html

## Decision

An operation whose after-bytes are its before-bytes plus a non-empty suffix stores only
the suffix (compressed, like every image) and the before length:
`before = {"sha256", "length"}`, `after = {"sha256", "base_length", "suffix",
"suffix_sha256"}`. This is SQLite's own rule — keep what a rollback needs, and a
growing file needs only its original size — and Git's delta idea, with the base being
the file already on disk.

Every read materialises bytes from the target, which the transaction already checks
against a hash before it writes: redo publishes `current + suffix` when the target
hashes to `before`; undo and abort publish `current[:length]` when it hashes to
`after`; the result is hashed against the row before it is published, and the
publication itself keeps its temp-file-and-rename path — no in-place truncate, so the
existing fsync ordering and crash recovery are unchanged. A tampered plan cannot
restore wrong bytes: the result must match the database row's hash.

Plans are written as `markdown-transaction/v2`; `v1` plans (full images only) stay
readable, undoable and prunable. Code older than this change refuses a `v2` plan
through its schema instead of misreading it; the nightly update only moves forward.

Alternatives: compress harder (images already are; 2.58 GB was compressed); shorten
the undo window (rejected: the 2-day window is the owner's run/ deletion contract);
deltas for every replace (rejected for now: a general diff needs a diff format and
still stores the old text; 1 085 non-append operations took 4.8 MB). Trade-off: undo of
an append needs the target to still equal its after-state — the same condition undo
already requires.
