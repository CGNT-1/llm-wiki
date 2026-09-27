"""A PowerShell command a test builds quotes its values with `ps_literal`, not JSON.

PowerShell does not read a backslash as an escape, so a JSON-quoted Windows path
reached the script with doubled separators and a path compared as text failed on
Windows only (PR #45). See
`docs/research/2026-09-27-a-powershell-path-is-a-single-quoted-literal.md`.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# A Verb-Noun command (`Get-ClaudeMcpState`, `Invoke-Expression`): text only PowerShell writes.
_POWERSHELL_TEXT = re.compile(r"\b[A-Z][a-z]+-[A-Z][A-Za-z]+")


def _literal_text(node: ast.JoinedStr) -> str:
    parts = [part.value for part in node.values if isinstance(part, ast.Constant)]
    return "".join(str(part) for part in parts)


def _json_quoted_values(node: ast.JoinedStr) -> list[str]:
    values = [part.value for part in node.values if isinstance(part, ast.FormattedValue)]
    return [ast.unparse(value) for value in values if ast.unparse(value).startswith("json.dumps(")]


def _powershell_strings(tree: ast.Module) -> list[ast.JoinedStr]:
    strings = [node for node in ast.walk(tree) if isinstance(node, ast.JoinedStr)]
    return [node for node in strings if _POWERSHELL_TEXT.search(_literal_text(node))]


def _named(path: Path, node: ast.JoinedStr) -> list[str]:
    return [f"{path.name}:{node.lineno}: {value}" for value in _json_quoted_values(node)]


def _offences(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return [offence for node in _powershell_strings(tree) for offence in _named(path, node)]


def test_no_powershell_command_quotes_a_value_as_json() -> None:
    tests = sorted(path for path in (ROOT / "tests").glob("*.py") if path.name != Path(__file__).name)
    assert [offence for path in tests for offence in _offences(path)] == []


def test_the_guard_sees_a_json_quoted_path(tmp_path: Path) -> None:
    source = tmp_path / "sample.py"
    source.write_text(
        "import json\n"
        "command = f\"Get-ClaudeMcpState -VaultRoot {json.dumps(str(root))}\"\n",
        encoding="utf-8",
    )
    assert _offences(source) == ["sample.py:2: json.dumps(str(root))"]
