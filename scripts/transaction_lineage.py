"""What ties a refused (quarantined) transaction to the commit that resolved it.

`doctor` reads these ties to decide whether a quarantined attempt is history; the
history prune must keep every row that serves as such a tie, or a resolved
quarantine turns into a permanent finding once its witness is pruned (audit
2026-09-27 A-6, docs/research/2026-09-27-a-prune-keeps-what-resolves-a-quarantine.md).
One place for both, so the prune cannot drift from what the health check reads.
"""

from __future__ import annotations

import re
import sqlite3

_RETRY_ORDINAL_SUFFIX = re.compile(r"(?::cas:\d+|#\d+)+$")
_CHECKPOINT_ATTEMPT_ORDINAL = re.compile(r"^(project:[^:]+:\d+):attempt:\d+:epoch:\d+:([0-9a-f]+)$")


def base_operation_identity(operation_id: str) -> str:
    """The identity a retry ordinal was derived from.

    Both suffix retry paths build the next attempt by suffixing the identity
    they are retrying: `:cas:<n>` for a losing append, `#<n>` for a refused
    attempt of any other kind. Stripping the suffixes recovers the request the
    whole chain is about.

    Project checkpoints write their ordinal in the middle instead:
    `project:<slug>:<sequence>:attempt:<n>:epoch:<m>:<digest>`, where a retry
    takes the next attempt number and a fresh fencing epoch while the slug,
    the sequence, and the payload digest stay. Removing the attempt/epoch pair
    recovers the same request identity. The digest is deliberately kept: a
    different payload committed at the same sequence proves nothing about this
    attempt's content, so it must never resolve it.
    """
    stripped = _RETRY_ORDINAL_SUFFIX.sub("", operation_id)
    match = _CHECKPOINT_ATTEMPT_ORDINAL.match(stripped)
    return f"{match.group(1)}:{match.group(2)}" if match else stripped


def _parent_by_transaction(database: sqlite3.Connection) -> dict[str, str]:
    return {
        row[0]: row[1]
        for row in database.execute(
            'SELECT id, parent_transaction_id FROM "transaction" '
            "WHERE parent_transaction_id IS NOT NULL"
        )
    }


def _mark_ancestors(
    identifier: str | None, parents: dict[str, str], resolved: set[str]
) -> None:
    while identifier and identifier not in resolved:
        resolved.add(identifier)
        identifier = parents.get(identifier)


def chain_resolved_ids(database: sqlite3.Connection) -> set[str]:
    """Every attempt whose own chain of retries ended in a commit.

    One hop is not enough: a retry can be refused too, and the ordinals
    (`<id>:cas:2` for an append, `<id>#3` for a compile) exist precisely
    because of that. Reading only the parent a committed row names left the
    first refusal of a three-deep chain open forever, which is the same
    permanently red finding the lineage was introduced to prevent.
    """
    parents = _parent_by_transaction(database)
    resolved: set[str] = set()
    for row in database.execute(
        'SELECT parent_transaction_id FROM "transaction" '
        "WHERE state='committed' AND parent_transaction_id IS NOT NULL"
    ):
        _mark_ancestors(row[0], parents, resolved)
    return resolved


def _committed_base_identities(database: sqlite3.Connection) -> set[str]:
    return {
        base_operation_identity(row[0])
        for row in database.execute(
            'SELECT operation_id FROM "transaction" WHERE state=\'committed\''
        )
    }


def ordinal_resolved_ids(database: sqlite3.Connection) -> set[str]:
    """Attempts a committed retry of the same operation identity replaced.

    The lineage is the same fact as `parent_transaction_id`, recorded in the
    operation identity instead of the parent column, and it is the only copy
    that survives for the append races refused before the parent was being
    written. `committed_attempt` already resolves an identity to the attempt
    that committed this way; the health check simply did not ask.

    This is narrower than it looks, and deliberately so. It resolves an attempt
    only when a commit carries *its own* request identity, which is derived
    from the payload — never because some other transaction happened to write
    the same file. A genuinely lost append leaves no such sibling and stays a
    finding.
    """
    committed = _committed_base_identities(database)
    return {
        row[0]
        for row in database.execute(
            'SELECT id, operation_id FROM "transaction" WHERE state=\'quarantined\''
        )
        if base_operation_identity(row[1]) in committed
    }


def committed_created_paths(database: sqlite3.Connection) -> set[str]:
    return {
        row[0]
        for row in database.execute(
            'SELECT operation.path FROM operation JOIN "transaction" '
            "ON operation.transaction_id = \"transaction\".id "
            "WHERE \"transaction\".state='committed' AND operation.kind='create'"
        )
    }


def outcome_was_written(
    database: sqlite3.Connection, identifier: str, committed_creates: set[str]
) -> bool:
    """Everything this refused attempt meant to create was created by a commit."""
    intended = {
        row[0]
        for row in database.execute(
            "SELECT path FROM operation WHERE transaction_id = ? AND kind = 'create'",
            (identifier,),
        )
    }
    if not intended:
        return False
    return intended <= committed_creates


def resolved_by_lineage(database: sqlite3.Connection) -> set[str]:
    """Both records of the same fact: a retry of this attempt committed."""
    return chain_resolved_ids(database) | ordinal_resolved_ids(database)


def resolved_quarantines(database: sqlite3.Connection) -> frozenset[str]:
    """Quarantined attempts the transaction rows alone show resolved.

    The retry lineage, or the outcome (everything the attempt meant to create was
    created by a commit). doctor's fourth proof, a compile superseded by a later
    one, reads the attempt's staged files, so it is not decided from rows.
    """
    open_attempts = {
        str(row[0]) for row in database.execute('SELECT id FROM "transaction" WHERE state=\'quarantined\'')
    }
    lineage = open_attempts & resolved_by_lineage(database)
    creates = committed_created_paths(database)
    outcome = {ident for ident in open_attempts - lineage if outcome_was_written(database, ident, creates)}
    return frozenset(lineage | outcome)


def _rows(database: sqlite3.Connection) -> list[tuple[str, str, str, str | None]]:
    return [
        (str(row[0]), str(row[1]), str(row[2]), row[3])
        for row in database.execute('SELECT id, operation_id, state, parent_transaction_id FROM "transaction"')
    ]


def _same_request(rows: list[tuple[str, str, str, str | None]], quarantined: set[str]) -> set[str]:
    """Rows carrying the request identity of a quarantined one: its retries."""
    bases = {base_operation_identity(operation) for ident, operation, _s, _p in rows if ident in quarantined}
    return {ident for ident, operation, _s, _p in rows if base_operation_identity(operation) in bases}


def _path_to_quarantine(ident: str, parents: dict[str, str | None], quarantined: set[str]) -> list[str]:
    """The chain from this row up to a quarantined ancestor, or [] when none."""
    chain: list[str] = []
    current: str | None = ident
    while current is not None and current not in chain:
        chain.append(current)
        if current in quarantined:
            return chain
        current = parents.get(current)
    return []


def _parent_chains(rows: list[tuple[str, str, str, str | None]], quarantined: set[str]) -> set[str]:
    """Every row on a parent chain that reaches a quarantined attempt."""
    parents = {ident: parent for ident, _o, _s, parent in rows}
    return {member for ident in parents for member in _path_to_quarantine(ident, parents, quarantined)}


def _same_created_paths(database: sqlite3.Connection, quarantined: set[str]) -> set[str]:
    """Committed rows that created a path a quarantined attempt meant to create."""
    intended = {
        str(row[1])
        for row in database.execute("SELECT transaction_id, path FROM operation WHERE kind = 'create'")
        if row[0] in quarantined
    }
    return {
        str(row[0])
        for row in database.execute(
            'SELECT operation.transaction_id, operation.path FROM operation JOIN "transaction" '
            'ON operation.transaction_id = "transaction".id '
            "WHERE \"transaction\".state = 'committed' AND operation.kind = 'create'"
        )
        if row[1] in intended
    }


def quarantine_witnesses(database: sqlite3.Connection) -> frozenset[str]:
    """Every transaction that ties a quarantined attempt to its resolution."""
    rows = _rows(database)
    quarantined = {ident for ident, _o, state, _p in rows if state == "quarantined"}
    if not quarantined:
        return frozenset()
    ties = _same_request(rows, quarantined) | _parent_chains(rows, quarantined)
    return frozenset(ties | _same_created_paths(database, quarantined))
