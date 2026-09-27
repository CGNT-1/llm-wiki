"""A signal handler never writes through a buffered stream.

`print` in the setsid fixture's SIGTERM handler re-entered stdout's buffer when the
signal landed during the previous `print`, and the fixture died with `RuntimeError:
reentrant call`. See
`docs/research/2026-09-27-a-signal-handler-writes-without-a-buffer.md`.
"""

from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_BUFFERED_STREAMS = {"stdout", "stderr"}


def _handler_name(node: ast.AST) -> str | None:
    """The handler named in `signal.signal(<signum>, <handler>)`, or None."""
    if not isinstance(node, ast.Call) or ast.unparse(node.func) != "signal.signal":
        return None
    handler = node.args[1] if len(node.args) == 2 else None
    return handler.id if isinstance(handler, ast.Name) else None


def _registered_handlers(tree: ast.Module) -> set[str]:
    """Names passed as the handler to `signal.signal(<signum>, <handler>)`."""
    names = {_handler_name(node) for node in ast.walk(tree)}
    return {name for name in names if name is not None}


_BUFFERED_WRITES = {
    f"sys.{stream}{suffix}"
    for stream in _BUFFERED_STREAMS
    for suffix in (".write", ".writelines", ".flush", ".buffer.write", ".buffer.flush")
} | {"print"}


def _buffered_write(node: ast.AST) -> bool:
    """`print(...)`, or a write or flush through `sys.stdout` / `sys.stderr` (not `fileno()`)."""
    return isinstance(node, ast.Call) and ast.unparse(node.func) in _BUFFERED_WRITES


def _writes_buffered(function: ast.FunctionDef) -> bool:
    return any(_buffered_write(node) for node in ast.walk(function))


def _handler_functions(tree: ast.Module) -> list[ast.FunctionDef]:
    handlers = _registered_handlers(tree)
    functions = [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
    return [function for function in functions if function.name in handlers]


def _offending_handlers(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    offending = [function for function in _handler_functions(tree) if _writes_buffered(function)]
    return [f"{path.relative_to(ROOT)}::{function.name}" for function in offending]


def _code_files() -> list[Path]:
    """Python the project runs; `tests/fixtures/` holds inputs, some deliberately unparseable."""
    candidates = sorted((ROOT / "scripts").rglob("*.py")) + sorted((ROOT / "tests").rglob("*.py"))
    return [path for path in candidates if "fixtures" not in path.relative_to(ROOT).parts]


def test_no_signal_handler_writes_through_a_buffered_stream() -> None:
    sources = _code_files()
    offending = [name for path in sources for name in _offending_handlers(path)]
    assert offending == []


def test_the_guard_sees_a_print_in_a_handler(tmp_path: Path) -> None:
    source = tmp_path / "handler.py"
    source.write_text(
        "import signal\n"
        "def _on_term(_s, _f):\n"
        "    print('bye', flush=True)\n"
        "signal.signal(signal.SIGTERM, _on_term)\n",
        encoding="utf-8",
    )
    tree = ast.parse(source.read_text(encoding="utf-8"))
    function = next(node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef))
    assert _registered_handlers(tree) == {"_on_term"}
    assert any(_buffered_write(node) for node in ast.walk(function))
