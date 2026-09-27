# Every function holds two `if` statements

Date: 2026-09-27. Audit 2026-09-27, law 5, second part (the first part is
`2026-09-27-a-function-holds-two-ifs.md`).

## Requirement

The owner's law 5: "При появлении более двух if в одной функции внутреннюю логику
необходимо выделять в независимые подфункции." It is not what lizard measures: lizard
reports "the nloc (lines of code without comments), CCN (cyclomatic complexity
number), token count of functions, [and] parameter count of functions"
(https://github.com/terryyin/lizard), so a function with three `if` statements and
CCN 4 passed every gate.

## Measured

An AST counter (own `if`/`elif` nodes per function, nested functions counted as their
own) found 91 functions over the rule in `scripts/` on 44517ee9 — the four fixed in the
first part are not among them. After this change: 2, both in
`scripts/private_vault_backup.py` (below). Outside `scripts/`: 31 in `tests/` and 5 in
`benchmark/`, handled separately.

## Method

Pure extraction (Fowler's catalog: Extract Function,
https://refactoring.com/catalog/extractFunction.html; Replace Nested Conditional with
Guard Clauses, https://refactoring.com/catalog/replaceNestedConditionalWithGuardClauses.html):
the inner step of each function moved into a helper; messages, exception types, the
order of side effects, locking and public names unchanged; platform branches keep
their exact conditions. Where two functions repeated the same body the copy went
(`workspace_revision` global git paths, `pyright_session` chunk loop,
`lsp_process._require_generation_nonce`, `markdown_transaction._hash_opened_target`).
One timing detail changed on purpose: the v3 queue reader's `heartbeat` and `fail` now
read the clock inside their transaction through `_with_verified_lease`, as every
sibling method on that path already did.

## Not done

`private_vault_backup._validate_command` and `_validate_root_locations` keep three
`if` statements: the machine's rule-8 gate refuses every edit of that file, reading
"backup" in its name as a leftover copy. The split is ready
(`_valid_command_item`, `_require_separate_sources`). The gate belongs to the machine
owner; it is not bypassed. The guard names both functions with the removal condition.

## Guard

`tests/test_a_function_holds_two_ifs.py` now walks all of `scripts/` and asserts the
offenders are exactly the two named ones.
