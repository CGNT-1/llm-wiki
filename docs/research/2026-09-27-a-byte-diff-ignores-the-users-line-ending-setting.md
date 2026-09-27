# A byte diff ignores the user's line-ending setting

Date: 2026-09-27. Scope: `scripts/impact_analysis.py::_git_hunks`, which compares two
temporary files with `git diff --no-index` (audit 2026-09-27 A-5).

## What failed

PR #45 failed `tests/test_a_line_ending_is_not_an_edit.py::test_a_change_of_line_endings_alone_is_still_a_change`
on three Windows jobs and passed on Linux. Reproduced here with a `~/.gitconfig` holding
`core.autocrlf = true` (the setting Git for Windows installs): 1 failed, 2 passed;
without it, 3 passed. `sanitized_git_environment` strips `GIT_CONFIG*` variables but
Git still reads the user's and the system's configuration files, so the byte diff of
two scratch files inherited the checkout-oriented end-of-line conversion and a
CRLF-only change produced no hunk.

## Sources

- gitattributes(5): "This attribute marks the path as a text file, which enables
  end-of-line conversion: When a matching file is added to the index, the file's line
  endings are normalized to LF in the index." and "If you simply want to have CRLF line
  endings in your working directory regardless of the repository you are working with,
  you can set the config variable "core.autocrlf" without using any attributes."
  https://git-scm.com/docs/gitattributes
- git(1), `-c <name>=<value>`: "Pass a configuration parameter to the command. The
  value given will override values from configuration files."
  https://git-scm.com/docs/git
- GitHub Docs, Configuring Git to handle line endings: "On Windows, you simply pass
  `true` to the configuration." — so a Windows machine is expected to carry it.
  https://docs.github.com/en/get-started/git-basics/configuring-git-to-handle-line-endings

## Decision

`_DIFF_ARGUMENTS` passes `-c core.autocrlf=false`: this diff compares bytes the caller
already holds, and conversion is exactly what it must not do. The other Git calls in
the module read the real checkout, where the user's conversion is correct, and keep it.

Alternatives: skip the test on Windows (rejected — masks a real defect on the platform
that has it); diff in Python again (rejected — A-5 moved to Git for its linear-time
diff); drop all user configuration for every Git call (rejected — the checkout calls
need it). Remaining limit: a user `core.attributesFile` that marks every path `text`
could still convert; no such case is known, and the test above would show it.

## Guard

The test module now runs every case under a `HOME` whose `.gitconfig` sets
`core.autocrlf = true`, so Linux CI meets the Windows condition.
