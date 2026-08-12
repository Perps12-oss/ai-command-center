"""Workspace OS launch capabilities, dispatched via TOOL_INVOKE (G2).

Workspace OS launches used to run through ``ActionRegistry`` directly from
``UI_LAUNCH_RESOURCE``, producing real side effects (``webbrowser.open``,
``os.startfile``, ``subprocess.run``) with no ExecutionAuthority decision, no
ExecutionReceipt and no TruthBoundary validation.

These wrappers place the *same* handlers below the execution boundary: the sole
``TOOL_INVOKE`` publisher (ExecutionOrchestratorService) dispatches them like any
other tool, so every launch now yields a receipt or fails closed.

The frozen handlers in ``core/workspace_os_actions.py`` are reused verbatim rather
than reimplemented — that module stays byte-identical (no constitutional
amendment required) and the side-effect code keeps a single source of truth
(Inv 11). ActionRegistry gains no execution authority; it is unchanged.
"""

from __future__ import annotations

from typing import Any

from ai_command_center.core.tools import ToolResult

# Frozen Phase 2 handlers — imported, never redefined. See module docstring.
from ai_command_center.core.workspace_os_actions import (
    _execute_command as _frozen_execute_command,
)
from ai_command_center.core.workspace_os_actions import (
    _launch_url as _frozen_launch_url,
)
from ai_command_center.core.workspace_os_actions import (
    _open_folder as _frozen_open_folder,
)


def _tool_result(facts: dict[str, Any], output: str) -> ToolResult:
    success = bool(facts.get("success"))
    return ToolResult(
        success=success,
        output=output if success else "",
        error="" if success else str(facts.get("stderr") or "launch failed"),
        facts=dict(facts),
    )


def run_workspace_open_url(args: dict[str, Any]) -> ToolResult:
    """Open a URL in the default browser (frozen ``_launch_url``)."""
    url = str(args.get("url") or "").strip()
    if not url:
        return ToolResult(success=False, output="", error="no url provided", facts={})
    try:
        facts = dict(_frozen_launch_url({"url": url}))
    except Exception as exc:  # surfaced as a failed receipt, never as success
        return ToolResult(
            success=False, output="", error=str(exc), facts={"url": url, "success": False}
        )
    facts.setdefault("launched", bool(facts.get("success")))
    return _tool_result(facts, f"Opened {url}")


def run_workspace_open_folder(args: dict[str, Any]) -> ToolResult:
    """Open a folder in the default file manager (frozen ``_open_folder``)."""
    path = str(args.get("path") or "").strip()
    if not path:
        return ToolResult(success=False, output="", error="no path provided", facts={})
    try:
        facts = dict(_frozen_open_folder({"path": path}))
    except Exception as exc:
        return ToolResult(
            success=False, output="", error=str(exc), facts={"path": path, "success": False}
        )
    facts.setdefault("launched", bool(facts.get("success")))
    return _tool_result(facts, f"Opened {path}")


def run_workspace_execute_command(args: dict[str, Any]) -> ToolResult:
    """Run a sandbox-validated command (frozen ``_execute_command``)."""
    command = str(args.get("command") or "").strip()
    if not command:
        return ToolResult(success=False, output="", error="no command provided", facts={})
    try:
        facts = dict(_frozen_execute_command({"command": command}))
    except Exception as exc:
        return ToolResult(
            success=False,
            output="",
            error=str(exc),
            facts={"command": command, "success": False},
        )
    output = str(facts.get("stdout") or "")
    facts.setdefault("output", output)
    return _tool_result(facts, output or f"Ran: {command}")


__all__ = [
    "run_workspace_execute_command",
    "run_workspace_open_folder",
    "run_workspace_open_url",
]
