# A PowerShell path is a single-quoted literal

Date: 2026-09-27. Scope: every PowerShell command a test builds in Python.

## What failed

PR #45 failed `tests/test_both_installers_read_the_claude_file_alike.py::test_install_ps1_reads_a_file_whose_keys_differ_by_case`
on three Windows jobs: `assert ['elsewhere'] == ['current']`. The test put the vault
path into the command as `json.dumps(str(ROOT))`. JSON escapes a backslash, PowerShell
does not read that escape, so `-VaultRoot` received `D:\\a\\...` with doubled
separators, which is a different string from the `D:\a\...` in the file. File APIs
tolerate the doubled separator, which is why the other sites of the same
shape passed and only a path compared as text failed.

## Sources

- RFC 8259 §7: "All Unicode characters may be placed within the quotation marks,
  except for the characters that MUST be escaped: quotation mark, reverse solidus,
  and the control characters (U+0000 through U+001F)."
  https://www.rfc-editor.org/rfc/rfc8259#section-7
- Microsoft, about_Quoting_Rules: "A string enclosed in single quotation marks is a
  verbatim string. The string is passed to the command exactly as you type it. No
  substitution is performed." and "To include a single quotation mark in a
  single-quoted string, use a second consecutive single quote."
  https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.core/about/about_quoting_rules
- The same page: the escape character is "the backtick character (`), which is the
  PowerShell escape character" — a backslash has no meaning there, and a double-quoted
  string also expands `$`.

## Decision

One helper, `tests/powershell_literal.py::ps_literal`, writes a value as a
single-quoted literal (only `'` doubled). It replaces three identical local copies
and every JSON-quoted value in a PowerShell command in `tests/`. JSON stays where the
target is JSON, JavaScript or TOML.

Alternatives: double-quoted PowerShell strings with backtick escaping (rejected — must
also escape `$`, more rules for the same result); normalise paths before comparing in
the product (rejected — the product was right; the test built the wrong input).

## Guard

`tests/test_a_powershell_path_is_a_single_quoted_literal.py` parses every test module
and fails on an f-string that carries PowerShell text (a Verb-Noun command) and a
`json.dumps(...)` value. On the tree before this change it named 39 values.
