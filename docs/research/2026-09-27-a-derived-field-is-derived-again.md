# A derived field is derived again

Date: 2026-09-27. Audit 2026-09-27, finding A-2 (my regression from B-14).

## What was wrong (reproduced)

B-14 made `_validate_semantic_operation` return the operation with a `project`
field derived from the quoted blocks. A validated operation is validated again
downstream — `validate_compile_plan`, `_planned_operation`, materialization — and
`_require_semantic_shape` refused the field it did not know: "compile operation has
unsupported semantic fields". Every plan whose evidence named a project failed, after
the provider had been paid. The B-14 test was unit-level and never sent a plan
through validation.

## Alternatives considered

1. Add `project` to the accepted fields. Rejected: the model could then supply a
   project of its own, and validation would stop being a pure function of its input.
2. Keep the project out of the operation and compute it only at render time.
   Rejected: the render path does not hold the bound evidence blocks; it would have
   to resolve them a second time.
3. Treat `project` as output-only: validation drops it and derives it again from the
   quoted bytes. Chosen. Validating twice gives the same operation, and a value the
   model sends is replaced, not trusted and not an error.

## Decision

`_DERIVED_FIELDS = {"project"}` in `compile_memory.py`; `_validate_semantic_operation`
removes those fields first and `_with_page_project` derives them again. Guard:
`tests/test_a_derived_field_is_derived_again.py` checks that validation is idempotent
(any derived field, not only this one), that the audit's plan validates and
materializes, and that a model-supplied `project` is replaced.

## Sources (fetched 2026-09-27)

- Google AIP-203, Field behavior, https://google.aip.dev/203 — `OUTPUT_ONLY`: "the
  field is provided in responses, but that including the field in a message in a
  request does nothing (the server must clear out any value in this field and must
  not throw an error as a result of the presence of a value in this field on input)."
- JSON Schema Validation 2020-12, §9.4, https://json-schema.org/draft/2020-12/json-schema-validation#section-9.4
  — "If 'readOnly' has a value of boolean true, it indicates that the value of the
  instance is managed exclusively by the owning authority, and attempts by an
  application to modify the value of this property are expected to be ignored or
  rejected by that owning authority."
- OpenAPI Specification 3.0.3, Schema Object, fetched 2026-09-27 from
  https://raw.githubusercontent.com/OAI/OpenAPI-Specification/main/versions/3.0.3.md —
  `readOnly`: "Declares the property as \"read only\". This means that it MAY be sent
  as part of a response but SHOULD NOT be sent as part of the request."
- Checked on the audit's own reproduction (not an independent source): re-run on the
  fixed code gives "revalidation OK", "validate_compile_plan OK" and a materialized path.

Conclusion (mine): all three specifications treat a server-derived field as
cleared-and-recomputed on input; that is exactly the property the compile needs.

## Files

- `scripts/compile_memory.py`
- `tests/test_a_derived_field_is_derived_again.py`
