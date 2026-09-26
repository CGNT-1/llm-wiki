# The checkpoint keys are indexed

Date: 2026-09-27. Audit 2026-09-27, finding B-1. Owner decision 2026-09-27: "Да,
добавить" (add the two indexes; recorded with `log_decision`).

## What was wrong (measured)

`project_checkpoints.transaction_id` and `project_checkpoint_attempts.transaction_id`
reference `"transaction"(id)` with no index, so every deleted transaction row makes
SQLite scan both tables. On a copy of the live coordinator database (read-only
backup): 400 deletes took 2.78 s without the indexes and 0.02 s with them; the
integrity and foreign-key checks stayed clean. The prune had already been made
sliced and deadline-bounded; the cost itself grows with the checkpoint tables.

## Decision and alternatives

The v3 coordinator schema is checked for an exact set of objects
(`_coordinator_v3_schema_complete`), and `COORDINATOR_V3_SCHEMA_SHA256` is recorded
in adoption manifests.

1. Add the indexes to the table SQL and change the schema digest. Rejected: every
   installed vault's recorded adoption would stop matching, and a database opened
   read-only (doctor, backup) before migrating would read as incomplete.
2. Chosen: two named indexes are *known optional* objects. A v3 database is complete
   with exactly the v3 tables plus none, one or both of these indexes (each as
   declared); any other object still makes it incomplete. The history prune creates
   them with `CREATE INDEX IF NOT EXISTS` inside its write transaction before it
   deletes — only for a v3 database, because the v2 migration source is validated
   against an exact object list. The schema digest names the table contract and is
   unchanged.

## Sources (fetched 2026-09-27)

- SQLite, Foreign Key Support §3, https://www.sqlite.org/foreignkeys.html — "If these
  queries cannot use an index, they are forced to do a linear scan of the entire
  child table. In a non-trivial database, this may be prohibitively expensive."
- SQLite, CREATE INDEX, https://www.sqlite.org/lang_createindex.html — "If the
  optional IF NOT EXISTS clause is present and another index with the same name
  already exists, then this command becomes a no-op."
- SQLite, The SQLite Query Optimizer Overview / query planning,
  https://www.sqlite.org/queryplanner.html — "If the table contains N elements, the
  time required to look up the desired row is proportional to logN rather than being
  proportional to N as in a full table scan."
- Martin Fowler, Evolutionary Database Design, https://martinfowler.com/articles/evodb.html —
  "Like code refactoring, database refactorings are very small." "Our automation
  ensures we never apply these changes manually, they are only applied by the
  automation tooling."

Conclusion (mine): a small additive change applied by the product itself, idempotent,
that older readers accept, fixes the documented cause without touching the contract
existing adoptions were recorded against.

## Guard

`tests/test_the_checkpoint_keys_are_indexed.py`: a v3 database built without the
indexes is complete; the history prune creates both and the database stays complete
(fails on the previous code); an unknown index still makes the schema incomplete.

## Files

- `scripts/markdown_transaction.py`
- `tests/test_the_checkpoint_keys_are_indexed.py`
