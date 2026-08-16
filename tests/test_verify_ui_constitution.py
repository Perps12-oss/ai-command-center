"""Ensure the UI Constitution gate stays green after Mission Control extraction."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def test_verify_ui_constitution_passes() -> None:
    result = subprocess.run(
        [sys.executable, str(REPO / "scripts" / "verify_ui_constitution.py")],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "UI Constitution gate passed." in result.stdout
