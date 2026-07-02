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
import sys
import webbrowser
from typing import TYPE_CHECKING

from ai_command_center.core.action.action import ACTION_TYPE_LAUNCH

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
    )

    # Folder launch: open a folder in the default file manager
    action_registry.register(
        action_type=ACTION_TYPE_LAUNCH,
        name="Open Folder",
        handler=_open_folder,
        parameters={"launch_type": "folder"},
        command_palette=True,
        ai_executable=False,
    )

    # Command launch: execute a shell command
    action_registry.register(
        action_type=ACTION_TYPE_LAUNCH,
        name="Execute Command",
        handler=_execute_command,
        parameters={"launch_type": "command"},
        command_palette=True,
        ai_executable=False,
    )


def _launch_url(parameters: dict) -> dict:
    """Launch a URL entity in the default browser."""
    url = parameters.get("url")
    if not url:
        raise ValueError("No URL provided for launch")
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


def _execute_command(parameters: dict) -> dict:
    """Execute a shell command and return the result."""
    command = parameters.get("command")
    if not command:
        raise ValueError("No command provided")
    command = str(command).strip()
    use_shell = any(ch in command for ch in "|&;<>$`")
    if use_shell:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
    else:
        argv = shlex.split(command, posix=(sys.platform != "win32"))
        result = subprocess.run(
            argv,
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
