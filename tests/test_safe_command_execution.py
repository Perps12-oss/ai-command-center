"""Tests verifying shell command execution no longer uses shell=True."""

from __future__ import annotations

from pathlib import Path

import pytest

from ai_command_center.core.workspace_os_actions import _execute_command
from ai_command_center.services.tool_executor_service import _run_shell_command


def test_run_shell_command_no_shell_injection(tmp_path: Path) -> None:
    """A redirection or pipe in the command string is not interpreted by the shell."""
    marker = tmp_path / "marker.txt"
    result = _run_shell_command({"command": f"python -c \"print(1+1)\" > {marker}"})
    assert result.success
    assert "2" in result.output
    assert not marker.exists()


def test_run_shell_command_rejects_invalid_syntax() -> None:
    """Unclosed quotes cause a clear error instead of invoking the shell."""
    result = _run_shell_command({"command": "python -c \"print(1"})
    assert not result.success
    assert "invalid command syntax" in result.error


def test_execute_command_no_shell_injection(tmp_path: Path) -> None:
    """The workspace action handler also parses the command safely."""
    marker = tmp_path / "marker.txt"
    result = _execute_command({"command": f"python -c \"print(1+1)\" > {marker}"})
    assert result["success"]
    assert "2" in result["stdout"]
    assert not marker.exists()


def test_execute_command_rejects_empty_command() -> None:
    with pytest.raises(ValueError, match="No command provided"):
        _execute_command({"command": ""})
