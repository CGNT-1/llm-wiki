# A previous state is a different file

Date: 2026-09-27. Audit 2026-09-27, finding C-20.

## What was wrong (checked on the live vault, read-only)

`update_state` hard-links the current `run/state.json` to `state.json.previous` and
then writes the new state. When the new state equals the old, `atomic_write` finds the
write a duplicate and does not replace the file — so both names stay on one inode.
Live, 2026-09-26: `state.json` and `state.json.previous` had inode 2391154, link count
2. `.previous` exists to recover from a damaged `state.json`; damage to that one inode
would take both.

## Alternatives considered

1. Copy the bytes instead of linking. Rejected: every hook writes state; a copy of
   the whole file on each write costs I/O for no gain over linking the replaced inode.
2. Chosen: serialize first; when the text equals the file, neither link nor write.
   A changed write links the old inode and replaces the name with a new one, so
   `.previous` is always a different file holding the version before the last change;
   unchanged writes also stop costing a write.

## Sources (fetched 2026-09-27)

- link(2), Linux man-pages, https://man7.org/linux/man-pages/man2/link.2.html —
  "link() creates a new link (also known as a hard link) to an existing file." …
  "both names refer to the same file".
- rename(2), Linux man-pages, https://man7.org/linux/man-pages/man2/rename.2.html
  (fetched 2026-09-26 for the staged-write note) — "If newpath already exists, it will
  be atomically replaced".
- Wikipedia, Hard link, https://en.wikipedia.org/wiki/Hard_link — "A process can open
  the file by any one of its paths and change its content."

Conclusion (mine): a link is a safe snapshot only of an inode that is about to lose
its name; linking the inode that keeps its name makes the "copy" the same file.

## Guard

`tests/test_a_previous_state_is_a_different_file.py` — change, change, unchanged:
`.previous` is not the same file as `state.json` and holds the version before the
last change (on the previous code: same file, and it held the current version).

## Files

- `scripts/memory_state.py`
- `tests/test_a_previous_state_is_a_different_file.py`
