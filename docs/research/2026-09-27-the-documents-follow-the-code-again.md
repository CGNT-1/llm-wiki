# The documents follow the code again

Date: 2026-09-27. Audit 2026-09-27, finding C-17.

## What was stale (facts, checked against the code)

- CLAUDE.md/AGENTS.md: a failed server start "is retried at most three times" — since
  7a4a65f9 a server that ran `HEALTHY_RUN_SECONDS` (600 s) before failing earns the
  budget back (`pyright_session.py`).
- USER-GUIDE and operating-model: "the one automatic Git operation is the nightly
  fast-forward" — the nightly also commits the `knowledge/` snapshot into its own local
  repository (`snapshot_knowledge.py`, `~/llm-wiki-snapshots/`).
- STRUCTURE: "proposed target" for the v3 adoption command, v3 receipts and the v3
  `run/` layout — all implemented and adopted by the installers.

## Decision

Each sentence now says what the code does; CLAUDE.md and AGENTS.md stay identical.
Guard: `tests/test_the_documents_say_what_the_code_does.py` refuses "one automatic Git
operation" and "proposed target" in the current documents, and requires CLAUDE.md to
name the healthy-run length the code uses.

## Source

- Diátaxis, https://diataxis.fr/ (fetched 2026-09-26): "Diátaxis identifies four
  distinct needs, and four corresponding forms of documentation - tutorials, how-to
  guides, technical reference and explanation." Reference must describe the machinery
  as it is.

## Files

- `CLAUDE.md`, `AGENTS.md`, `docs/USER-GUIDE.md`, `docs/operating-model.md`, `docs/STRUCTURE.md`
- `tests/test_the_documents_say_what_the_code_does.py`
