"""The installers' closing verdict is the sync's final doctor check, so it runs last.

A fresh install fetched the pinned model weights one step after that check, so
every fresh install that had the encoder runtime warned about weights it was
about to fetch, and its first generation was built without the vectors those
weights give. See docs/research/2026-09-27-the-install-checks-itself-last.md.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

# A script the installer runs: `python "<vault>/scripts/<name>.py"`, either slash.
_SCRIPT_RUN = re.compile(r'python "\$VAULT_ROOT[/\\]scripts[/\\](\w+)\.py"')


def _scripts_run(installer: str) -> list[str]:
    """The installer's script runs in the order it makes them."""
    return _SCRIPT_RUN.findall((ROOT / installer).read_text(encoding="utf-8"))


@pytest.mark.parametrize("installer", ["install.sh", "install.ps1"])
def test_the_sync_and_its_final_check_run_after_every_other_script(installer: str) -> None:
    runs = _scripts_run(installer)

    assert runs[-1] == "sync_memory", f"{installer} runs {runs[-1]} after the final check: {runs}"


@pytest.mark.parametrize("installer", ["install.sh", "install.ps1"])
def test_the_weights_are_fetched_before_the_first_generation_is_built(installer: str) -> None:
    runs = _scripts_run(installer)

    assert runs.index("install_models") < runs.index("sync_memory"), runs
