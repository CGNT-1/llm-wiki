# A function holds two `if` statements

Date: 2026-09-27. Audit 2026-09-27, law 5: four functions held three `if`
statements each — `integration_adapter._pending_checkpoints`, `_release_claims`,
`_restrict_file_permissions`, and `contradiction_pipeline.plan_candidate_changes`.

## Evidence

- The owner's law 5: "При появлении более двух if в одной функции внутреннюю
  логику необходимо выделять в независимые подфункции." The count is per
  function, nested `if` included; a nested function is its own function.
- The complexity gates (lizard CCN, nesting, ternary) do not count `if`
  statements, so all four passed them with CCN ≤ 5.
- Measured on the base commit with an AST counter: exactly these four in the two
  modules. Across `scripts/` the same counter finds 89 more functions over the
  rule; they are outside this change and are reported, not fixed here.

## Fix

Each function's inner step moved into a helper of its own: a split checkpoint
part and its observation; the existing `_pending_queue` reader (no second copy);
the Windows ACL call; one assessment's candidate file. Behaviour is unchanged,
covered by the existing suites of both modules.

## Guard

`tests/test_a_function_holds_two_ifs.py` counts `if` statements per function
in both modules and fails on the base commit (four names).

## Source

- Martin Fowler, *Refactoring*, 2nd ed., "Extract Function" —
  https://refactoring.com/catalog/extractFunction.html
