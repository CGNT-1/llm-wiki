"""A function holds at most two `if` statements (law 5).

The rule counts every `if` in one function, nested ones included; a nested
function is its own function. Audit 2026-09-27 found 93 functions over it in
`scripts/` (and 36 in `tests/` and `benchmark/`); all but two were split, and this guard holds every module to the
rule. See `docs/research/2026-09-27-a-function-holds-two-ifs.md` and
`docs/research/2026-09-27-every-function-holds-two-ifs.md`.
"""

from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAX_IFS = 2
_SCOPES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.ClassDef)

# Still over the rule, named here rather than skipped: the machine's rule-8 gate
# refuses every edit of `private_vault_backup.py`, reading the word "backup" in its
# name as a leftover copy, and the split below may not be forced past it. Remove each
# entry when that gate accepts edits to the file and the function is split
# (`_valid_command_item`; `_require_separate_sources`). The assertion is exact, so a
# fix that forgets this list, or a new offender, fails.
BLOCKED_BY_THE_BACKUP_NAME_GATE = {
    "scripts/private_vault_backup.py::_validate_command",
    "scripts/private_vault_backup.py::_validate_root_locations",
}


def _ifs(node: ast.AST) -> int:
    """The `if` statements this scope owns, without those of nested scopes."""
    children = [child for child in ast.iter_child_nodes(node) if not isinstance(child, _SCOPES)]
    return sum(isinstance(child, ast.If) + _ifs(child) for child in children)


def _functions(tree: ast.Module) -> list[ast.FunctionDef | ast.AsyncFunctionDef]:
    return [node for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))]


def _over_the_rule(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    name = path.relative_to(ROOT).as_posix()
    return {f"{name}::{node.name}" for node in _functions(tree) if _ifs(node) > MAX_IFS}


def test_the_counter_sees_nested_ifs_and_skips_nested_functions() -> None:
    source = "def f(x):\n    if x:\n        if x:\n            pass\n    def g():\n        if x: pass\n    if x: pass\n"
    function = ast.parse(source).body[0]
    assert _ifs(function) == 3


def _code_files() -> list[Path]:
    """The project's Python; `tests/fixtures/` holds inputs, some deliberately unparseable."""
    files = [path for folder in ("scripts", "tests", "benchmark") for path in (ROOT / folder).rglob("*.py")]
    return sorted(path for path in files if "fixtures" not in path.relative_to(ROOT).parts)


def test_no_function_holds_more_than_two_ifs() -> None:
    offenders = set().union(*(_over_the_rule(path) for path in _code_files()))
    assert offenders == BLOCKED_BY_THE_BACKUP_NAME_GATE
