"""One way to put a Python string into a PowerShell command a test builds.

A JSON string is not a PowerShell string: PowerShell does not treat a backslash as
an escape, so `json.dumps(r"D:\\a")` reached a script as `D:\\\\a` with doubled
separators. File APIs forgave it; a path compared as text did not, and a Windows
job failed (PR #45). A single-quoted literal is taken verbatim; only `'` is doubled.
See `docs/research/2026-09-27-a-powershell-path-is-a-single-quoted-literal.md`.
"""

from __future__ import annotations


def ps_literal(value: str) -> str:
    """`value` as a PowerShell single-quoted string literal."""
    return "'" + value.replace("'", "''") + "'"
