# A prune keeps what resolves a quarantine

Date: 2026-09-27. Audit 2026-09-27, findings A-6 (my regression, cc25fa2f with
9d1677ab) and B-1.

## What was wrong (reproduced on a copy of the live coordinator database)

- **A-6.** `doctor._unresolved_quarantine` treats a quarantined attempt as history
  when a committed row ties it to a resolution: a retry of the same request identity,
  a row on its parent chain, or a commit that created the files it meant to create.
  The 90-day history prune protected only rows a checkpoint names, so it deleted those
  witnesses: on the copy the unresolved count went from 1 to 96. No data is lost, but
  doctor stays red for good. First effect: about late November on this vault.
- **B-1.** The prune ran as one write transaction with no deadline. Every deleted
  `"transaction"` row makes SQLite scan `project_checkpoints` and
  `project_checkpoint_attempts`, whose `transaction_id` references have no index:
  828 rows took 34 s, 23 272 took 110.7 s; with indexes, 828 took 0.24 s. Inside the
  180 s reclaim step it could be killed and rolled back every night.

## Alternatives considered

1. Add the two indexes. This is the real cure for the cost, but the v3 coordinator
   schema is checked for an exact set of objects (`_coordinator_v3_schema_complete`,
   `COORDINATOR_V3_SCHEMA_SHA256`); an index is a change of the Reliability v3
   database contract and needs the owner's explicit decision. Not done here; asked.
2. Keep the whole prune transaction and only add a deadline check. Rejected: a killed
   transaction is rolled back, so a slow night keeps nothing.
3. Chosen: compute the witnesses once (`transaction_lineage.quarantine_witnesses`,
   the same ties doctor reads, now in one module both import), exclude them, and
   delete the remaining candidates in slices, each committed, re-checking every row's
   conditions at delete time, until the step's deadline. A late prune keeps what it
   did and reports `unfinished`.

Slice length: `HISTORY_SLICE_SECONDS = BREADCRUMB_APPEND_BUDGET_SECONDS / 2` — a hook's
breadcrumb append has 2.5 s for its whole write; a slice holds the writer gate for at
most half of that, so an append that arrives as a slice starts keeps half its time.

## Sources (fetched 2026-09-27)

- SQLite, Foreign Key Support, §3, https://www.sqlite.org/foreignkeys.html — "each
  time an application deletes a row from the artist table (the parent table), it
  performs the equivalent of the following SELECT statement to search for referencing
  rows … If these queries cannot use an index, they are forced to do a linear scan of
  the entire child table. In a non-trivial database, this may be prohibitively
  expensive."
- SQLite, BEGIN TRANSACTION, https://www.sqlite.org/lang_transaction.html — "IMMEDIATE
  causes the database connection to start a new write immediately … The BEGIN
  IMMEDIATE might fail with SQLITE_BUSY if another write transaction is already active
  on another database connection."
- Microsoft Learn, Resolve blocking problems caused by lock escalation,
  https://learn.microsoft.com/en-us/troubleshoot/sql/database-engine/performance/resolve-blocking-problems-caused-lock-escalation —
  "Break up large batch operations into several smaller operations." "By removing these
  records a few hundred at a time, you can dramatically reduce the number of locks that
  accumulate per transaction."

Conclusion (mine): the cost has its documented cause (unindexed child keys); until the
schema decision, short committed slices under the deadline keep every night's progress
and keep the writers' wait short.

## Guard

`tests/test_a_prune_keeps_what_resolves_a_quarantine.py`:
- builds each of the three kinds of resolution in a real coordinator, prunes past the
  window, and requires doctor's unresolved count to stay 0 (the old prune reopened
  3 of 3) while the unrelated row goes;
- a prune past its deadline deletes nothing and says `unfinished`; a sliced one
  finishes.

## Files

- `scripts/transaction_lineage.py` (new; `base_operation_identity` moved here from doctor)
- `scripts/markdown_transaction.py`, `scripts/doctor.py`, `scripts/reclaim_runtime_state.py`
- `tests/test_a_prune_keeps_what_resolves_a_quarantine.py`,
  `tests/test_doctor_quarantine_lineage.py`, `tests/test_doctor_checkpoint_lineage.py`
