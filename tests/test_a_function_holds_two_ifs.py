"""A function holds at most two `if` statements (law 5).

The rule counts every `if` in one function, nested ones included; a nested
function is its own function. Audit 2026-09-27 found four functions over it in
these two modules; this guard keeps the modules at the rule. See
`docs/research/2026-09-27-a-function-holds-two-ifs.md`.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
MAX_IFS = 2
_SCOPES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.ClassDef)


def _ifs(node: ast.AST) -> int:
    """The `if` statements this scope owns, without those of nested scopes."""
    children = [child for child in ast.iter_child_nodes(node) if not isinstance(child, _SCOPES)]
    return sum(isinstance(child, ast.If) + _ifs(child) for child in children)


def _over_the_rule(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    functions = [node for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))]
    return [f"{node.name}:{node.lineno} has {_ifs(node)}" for node in functions if _ifs(node) > MAX_IFS]


def test_the_counter_sees_nested_ifs_and_skips_nested_functions() -> None:
    source = "def f(x):\n    if x:\n        if x:\n            pass\n    def g():\n        if x: pass\n    if x: pass\n"
    function = ast.parse(source).body[0]
    assert _ifs(function) == 3


@pytest.mark.parametrize("module", ["scripts/integration_adapter.py", "scripts/contradiction_pipeline.py"])
def test_no_function_holds_more_than_two_ifs(module: str) -> None:
    assert _over_the_rule(ROOT / module) == []
