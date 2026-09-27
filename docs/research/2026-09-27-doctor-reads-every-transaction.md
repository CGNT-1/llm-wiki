# Doctor reads every transaction

Date: 2026-09-27. Scope: `scripts/doctor.py`, the transaction health check (law 7, law 9).

## Finding

`doctor.MAX_OPERATIONAL_ROWS = 10_000` capped the transaction and operation scans.
The installed vault holds 29 275 transactions and 37 509 operations (read-only count,
2026-09-27), so every report carried `transaction_scan_truncated` and
`transaction_operation_scan_truncated`, judged a third of the rows, and abstained from
the operation check entirely. The quarantine count (`quarantined_unresolved`) was not
affected: it is computed by `transaction_lineage` over whole tables.

Measured on a copy of the live database (python `sqlite3` backup API, never the CLI,
never the live file):

| code | rows judged | time | Python peak | verdict codes |
|---|---|---|---|---|
| HEAD 986895e9 | 10 000 of 29 369 | 0.52 s | 22.6 MB | `…metadata_corrupt`, both `*_truncated` |
| this change | 29 369 of 29 369 | 0.63 s | 14.4 MB | `…metadata_corrupt` only |

The capped scan was not buying anything: the whole scan costs 0.11 s more.

Two more defects of the same family (a verdict about the bound, not the rows) showed up
while testing:

- **The capped scan accused a healthy vault.** A synthetic vault of 10 200 healthy
  transactions with one operation each read as `transaction_metadata_corrupt` on HEAD.
- **The undo-directory listing has its own cap** (`MAX_RUNTIME_ENTRIES = 10_000`). A
  row whose `run/transactions/<id>` lay past the listing looked like a row whose
  directory is missing, and was called corrupt. The installed vault held 5 547 entries
  in the morning and 5 990 in the afternoon of 2026-09-27.
- **Quarantined before planning.** `_commit_promotion` writes the plan hash and the
  operations in one database transaction. When binding the project reservation
  refuses, that transaction rolls back and `_quarantine_failed_promotion` sets the row
  `quarantined` with `plan_hash = ''` and no operations. Doctor exempted only
  `preparing` and `discarded`, so these rows were corrupt metadata. There are 9 on the
  installed vault, and with the live undo directory they were the only rows
  `transaction_metadata_corrupt` rested on: that finding is what the session-start
  health line reported as "a transaction in a state this runtime does not define".

## Sources

- SQLite, Isolation In SQLite: "In rollback mode, SQLite implements isolation by
  locking the database file and preventing any reads by other database connections
  while each write transaction is underway. … before any changes are made to the
  database file on disk, all readers must be (temporarily) expelled in order to give
  the writer exclusive access to the database file." https://www.sqlite.org/isolation.html
- SQLite, Transaction: "Automatically started transactions are committed when the last
  SQL statement finishes." and "If the first statement after BEGIN DEFERRED is a
  SELECT, then a read transaction is started." https://www.sqlite.org/lang_transaction.html
- Python, sqlite3: `fetchmany` "Return the next set of rows of a query result as a
  list. Return an empty list if no more rows are available."; with `isolation_level`
  set to `None`, "transactions are never implicitly opened."
  https://docs.python.org/3/library/sqlite3.html

## Decision

- Both tables are streamed whole in batches of `SCAN_BATCH_ROWS = 1 000`, so memory
  holds one batch and the known ids and operation positions, not the tables; the
  deadline is checked between batches.
- The id, operation and transaction reads run in one read transaction (`BEGIN` …
  `COMMIT`). The read connection autocommits, so each statement used to see its own
  state, and a transaction committed between the reads looked like a row without
  operations or an operation of an unknown row. In rollback-journal mode the read
  transaction holds writers off for the scan (0.63 s on the installed vault), within
  their busy timeout.
- The operation read has no join: an operation whose transaction is gone reaches the
  identity check instead of vanishing.
- An incomplete undo listing abstains from the per-row directory comparison; the
  deletion refusal (`transaction_artifact_state_unknown`) stays.
- A row quarantined straight out of `preparing` (empty plan hash, no operations) is
  valid; a quarantined row with a plan still needs its operations.
- Removed with the cap (law 8): the `*_scan_truncated` codes, `transaction_scan_incomplete`,
  the "lower bound" verdict, the separate whole-table state count, and their tests.
  `MAX_OPERATIONAL_ROWS` stays for the small owner, lease and queue tables.

Alternatives rejected: raise the cap (the next vault outgrows it again; law 9 wants a
basis, and the measured cost says none is needed); answer every check with SQL
aggregates (the row checks parse JSON and compare to the filesystem, so they need the
rows; streaming gives the same bounded memory without a second implementation).

## Guard

`tests/test_doctor_bounded_scan_truth.py`: vaults past the old cap are read whole and
clean; a defect in the oldest row, a missing operation past the old operation cap and
an orphan operation are found; a quarantine before planning is not corrupt and a
planned one without operations is; an undo listing past its bound refuses deletion
without accusing. Six of its fifteen tests fail on HEAD.

## Not verified here

On the live undo directory, 70 entries named no transaction row at the time of the
check. Some may be skew between the database copy and the later listing; whether
committed rows are dropped from history while their directories stay is not checked.
