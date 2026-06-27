"""
Workspace OS Action Registration - FROZEN PATTERN

All Workspace OS actions are registered here. This module owns no business logic;
it only binds action types to handlers. The WorkspaceOsService orchestrates the
registration call during its lifecycle load.

FROZEN: Phase 2 - Workspace OS Integration
DO NOT MODIFY without constitutional amendment.
"""

from __future__ import annotations

import os
import shlex
import subprocess
import webbrowser
from typing import TYPE_CHECKING

from ai_command_center.core.action.action import ACTION_TYPE_LAUNCH
from ai_command_center.core.permission.permission import Permission

if TYPE_CHECKING:
    from ai_command_center.core.action.action_registry import ActionRegistry


def register_workspace_os_actions(action_registry: ActionRegistry) -> None:
    """Register all built-in Workspace OS actions."""
    # URL launch: open a URL in the default browser
    action_registry.register(
        action_type=ACTION_TYPE_LAUNCH,
        name="Launch URL",
        handler=_launch_url,
        parameters={"launch_type": "url"},
        command_palette=True,
        ai_executable=False,
        required_permissions=[Permission.EXECUTE_ACTION.value],
    )

    # Folder launch: open a folder in the default file manager
    action_registry.register(
        action_type=ACTION_TYPE_LAUNCH,
        name="Open Folder",
        handler=_open_folder,
        parameters={"launch_type": "folder"},
        command_palette=True,
        ai_executable=False,
        required_permissions=[Permission.EXECUTE_ACTION.value],
    )

    # Command launch: execute a shell command
    action_registry.register(
        action_type=ACTION_TYPE_LAUNCH,
        name="Execute Command",
        handler=_execute_command,
        parameters={"launch_type": "command"},
        command_palette=True,
        ai_executable=False,
        required_permissions=[Permission.LAUNCH_TOOL.value],
    )


def _launch_url(parameters: dict) -> dict:
    """Launch a URL entity in the default browser.

    Only ``http`` and ``https`` schemes are allowed to prevent arbitrary
    protocol handlers (e.g., ``file://``, ``javascript:``) from being opened.
    """
    url = str(parameters.get("url", "")).strip()
    if not url:
        raise ValueError("No URL provided for launch")
    allowed_schemes = {"http", "https"}
    parsed_scheme = url.split(":", 1)[0].lower() if ":" in url else ""
    if parsed_scheme not in allowed_schemes:
        raise ValueError(
            f"Invalid URL scheme for launch: {parsed_scheme or 'empty'}. "
            f"Allowed schemes: {', '.join(sorted(allowed_schemes))}"
        )
    success = webbrowser.open(url)
    return {"url": url, "success": success}


def _open_folder(parameters: dict) -> dict:
    """Open a folder in the default file manager."""
    path = parameters.get("path")
    if not path:
        raise ValueError("No folder path provided")
    if not os.path.isdir(path):
        raise FileNotFoundError(f"Folder not found: {path}")
    os.startfile(path)
    return {"path": path, "success": True}


def _parse_command(command: str) -> list[str] | None:
    """Parse a command string into a list of arguments for shell=False execution.

    ``shlex.split(posix=False)`` preserves Windows backslashes. Outer quotes are
    stripped because shlex with ``posix=False`` keeps them.
    """
    try:
        args = shlex.split(command, posix=False)
    except ValueError:
        return None
    return [arg.strip("\"'") for arg in args]


def _execute_command(parameters: dict) -> dict:
    """Execute a command and return the result.

    The command is parsed with ``shlex.split`` and executed with
    ``shell=False`` to prevent shell injection.
    """
    command = str(parameters.get("command", "")).strip()
    if not command:
        raise ValueError("No command provided")
    cmd_args = _parse_command(command)
    if cmd_args is None:
        return {
            "command": command,
            "success": False,
            "returncode": -1,
            "stdout": "",
            "stderr": "Invalid command syntax",
        }
    if not cmd_args:
        return {
            "command": command,
            "success": False,
            "returncode": -1,
            "stdout": "",
            "stderr": "Empty command after parsing",
        }
    result = subprocess.run(
        cmd_args,
        shell=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    return {
        "command": command,
        "success": result.returncode == 0,
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }
