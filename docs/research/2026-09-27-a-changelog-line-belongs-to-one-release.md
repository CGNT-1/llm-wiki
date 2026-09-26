# A changelog line belongs to one release

Date: 2026-09-27. Audit 2026-09-27, finding B-18 (my error in commit d1024c8a).

## What was wrong

A `sed` that inserted a line after "the first `### Fixed`" matched every `### Fixed`
heading, so one 2026-09-26 entry was written into the Unreleased section and into
five shipped sections (5.0.0, 4.0.0, 3.3.3, 3.3.2, 3.3.1). Released notes claimed a
fix that did not exist when they shipped. Nothing checked for it.

## Decision

- The five copies are removed; against tag v5.0.0 the file now differs only in the
  Unreleased section.
- New entries go through a helper that writes only inside `## [Unreleased]`.
- Guard: `tests/test_a_changelog_line_belongs_to_one_release.py` fails when any entry
  line appears in two release sections — the shape this error takes. It fails on the
  previous file; on the corrected file no other line repeats.

Alternative considered: compare each released section with its tag. Rejected for CI:
the checkout may lack tags; the duplicate check needs only the file.

## Sources (fetched 2026-09-27)

- Semantic Versioning 2.0.0, item 3, https://semver.org/ — "Once a versioned package
  has been released, the contents of that version MUST NOT be modified. Any
  modifications MUST be released as a new version."
- Keep a Changelog 1.1.0, https://keepachangelog.com/en/1.1.0/ — "Keep an `Unreleased`
  section at the top to track upcoming changes." "At release time, you can move the
  `Unreleased` section changes into a new release version section."
- GNU Coding Standards, Change Logs, https://www.gnu.org/prep/standards/html_node/Change-Logs.html —
  "The purpose of this is so that people investigating bugs in the future will know
  about the changes that might have introduced the bug."

## Files

- `CHANGELOG.md`
- `tests/test_a_changelog_line_belongs_to_one_release.py`
